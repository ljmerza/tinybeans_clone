"""Album API: list/create albums, view/rename/delete one, its posts, and adding/removing posts."""

import uuid

from django.db.models import Count, Exists, IntegerField, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce
from django.http import Http404
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, OpenApiTypes, extend_schema
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from mysite.circles.models import CircleMembership
from mysite.keeps.models import Keep, KeepMedia, KeepType
from mysite.keeps.serializers.feed import KeepFeedSerializer
from mysite.keeps.views.feed import KeepFeedPagination, feed_queryset, get_visible_keep_or_404
from mysite.users.models import UserRole

from .models import ALBUM_KEEP_ORDERING, Album, AlbumKeep
from .serializers import AlbumCreateSerializer, AlbumSerializer, AlbumUpdateSerializer


def _displayable_media():
    """Matches the feed: photos always, videos once a poster frame exists."""
    return KeepMedia.objects.filter(Q(media_type="photo") | Q(media_type="video", thumbnails_generated=True))


def visible_albums(user, *, keep=None):
    """Albums in the user's circles, annotated for ``AlbumSerializer``.

    ``post_count`` only counts posts the feed would show (text posts, or keeps
    with a displayable photo/video), so it matches the album page. The cover is
    the chosen ``cover_keep``'s first displayable photo while that post is still
    in the album, else the first displayable photo of the album's first post.
    With ``keep``, ``has_keep`` says whether that keep is in each album.
    """
    displayable = _displayable_media()
    visible_entries = AlbumKeep.objects.filter(album=OuterRef("pk")).filter(
        Q(keep__keep_type=KeepType.NOTE) | Exists(displayable.filter(keep=OuterRef("keep")))
    )
    post_count = Coalesce(
        Subquery(
            visible_entries.values("album").annotate(total=Count("id")).values("total"),
            output_field=IntegerField(),
        ),
        0,
    )
    media_order = ("upload_order", "id")
    chosen_cover = displayable.filter(
        keep=OuterRef("cover_keep"), keep__album_memberships__album=OuterRef("pk")
    ).order_by(*media_order)
    default_cover = displayable.filter(keep__album_memberships__album=OuterRef("pk")).order_by(
        *(f"keep__{field}" for field in ALBUM_KEEP_ORDERING), *media_order
    )
    # Mirrors the keeps' delete rule: the creator or a circle admin.
    circle_admin = CircleMembership.objects.filter(circle=OuterRef("circle"), user=user, role=UserRole.CIRCLE_ADMIN)

    albums = (
        Album.objects.filter(circle__memberships__user=user)
        .select_related("circle", "created_by")
        .order_by("-updated_at", "-created_at", "id")
        .annotate(
            post_count=post_count,
            cover_media_id=Coalesce(
                Subquery(chosen_cover.values("id")[:1]),
                Subquery(default_cover.values("id")[:1]),
            ),
            can_edit=Q(created_by=user) | Exists(circle_admin),
        )
    )
    if keep is not None:
        albums = albums.filter(circle_id=keep.circle_id).annotate(
            has_keep=Exists(AlbumKeep.objects.filter(album=OuterRef("pk"), keep=keep))
        )
    return albums


def attach_covers(albums):
    """Load every album's cover media in one query, as ``album.cover_media``."""
    albums = list(albums)
    ids = [album.cover_media_id for album in albums if album.cover_media_id]
    media = KeepMedia.objects.in_bulk(ids) if ids else {}
    for album in albums:
        album.cover_media = media.get(album.cover_media_id)
    return albums


def get_visible_album_or_404(user, album_id):
    """An album in one of the user's circles, annotated for ``AlbumSerializer``; 404 otherwise."""
    album = visible_albums(user).filter(pk=album_id).first()
    if album is None:
        raise Http404
    attach_covers([album])
    return album


class AlbumPagination(LimitOffsetPagination):
    default_limit = 50
    max_limit = 200


ALBUM_RESPONSE = OpenApiResponse(response=AlbumSerializer, description="The album")


class AlbumListCreateView(generics.ListCreateAPIView):
    """Albums in the viewer's circles (GET), or a new album (POST)."""

    serializer_class = AlbumSerializer
    pagination_class = AlbumPagination

    def get_queryset(self):
        # Avoid queryset evaluation during schema generation
        if getattr(self, "swagger_fake_view", False):
            return Album.objects.none()
        user = self.request.user
        keep_id = self.request.query_params.get("keep")
        keep = None
        if keep_id:
            try:
                keep_id = uuid.UUID(keep_id)
            except ValueError:
                raise Http404 from None
            keep = get_visible_keep_or_404(user, keep_id)
        albums = visible_albums(user, keep=keep)
        circle_slug = self.request.query_params.get("circle_slug")
        if circle_slug:
            albums = albums.filter(circle__slug=circle_slug)
        return albums

    def list(self, request, *args, **kwargs):
        page = self.paginate_queryset(self.get_queryset())
        serializer = self.get_serializer(attach_covers(page), many=True)
        return self.get_paginated_response(serializer.data)

    @extend_schema(
        summary="List albums",
        description="Albums in every circle the user belongs to, most recently changed first, each with its "
        "cover, post count and whether the viewer may edit it. Limit/offset paginated. With `keep`, only the "
        "albums of that post's circle, each with `has_keep`.",
        parameters=[
            OpenApiParameter(
                name="circle_slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Only albums in this circle",
            ),
            OpenApiParameter(
                name="keep",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                description="Only the albums of this post's circle, flagging the ones it is in",
            ),
            OpenApiParameter(
                name="limit",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Albums per page (default 50, max 200)",
            ),
            OpenApiParameter(
                name="offset", type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, description="Albums to skip"
            ),
        ],
        responses={
            200: OpenApiResponse(response=AlbumSerializer(many=True), description="A page of albums"),
            404: OpenApiResponse(description="`keep` not found or not visible to the user"),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Create an album",
        description="Any member of the circle can create an album, optionally adding a first post.",
        request=AlbumCreateSerializer,
        responses={201: ALBUM_RESPONSE, 400: OpenApiResponse(description="Invalid input or not your circle")},
    )
    def post(self, request, *args, **kwargs):
        serializer = AlbumCreateSerializer(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        album = serializer.save()
        album = get_visible_album_or_404(request.user, album.pk)
        return Response(self.get_serializer(album).data, status=status.HTTP_201_CREATED)


class AlbumDetailView(APIView):
    """One album: view (any member), rename/describe/set cover or delete (creator or circle admin)."""

    def _album_for_edit(self, request, album_id):
        album = get_visible_album_or_404(request.user, album_id)
        if not album.can_edit:
            raise PermissionDenied("Only the album's creator or a circle admin can change it.")
        return album

    @extend_schema(
        summary="Album",
        responses={200: ALBUM_RESPONSE, 404: OpenApiResponse(description="Not found or not visible to the user")},
    )
    def get(self, request, album_id):
        album = get_visible_album_or_404(request.user, album_id)
        return Response(AlbumSerializer(album, context={"request": request}).data)

    @extend_schema(
        summary="Update an album",
        description="Rename it, change its description or pick its cover post. Only its creator or a circle admin.",
        request=AlbumUpdateSerializer,
        responses={
            200: ALBUM_RESPONSE,
            400: OpenApiResponse(description="Invalid input"),
            403: OpenApiResponse(description="Not the creator or a circle admin"),
            404: OpenApiResponse(description="Not found or not visible to the user"),
        },
    )
    def patch(self, request, album_id):
        album = self._album_for_edit(request, album_id)
        serializer = AlbumUpdateSerializer(album, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        album = get_visible_album_or_404(request.user, album_id)
        return Response(AlbumSerializer(album, context={"request": request}).data)

    @extend_schema(
        summary="Delete an album",
        description="Deletes the album only; its posts stay. Only its creator or a circle admin.",
        responses={
            204: OpenApiResponse(description="Deleted"),
            403: OpenApiResponse(description="Not the creator or a circle admin"),
            404: OpenApiResponse(description="Not found or not visible to the user"),
        },
    )
    def delete(self, request, album_id):
        album = self._album_for_edit(request, album_id)
        Album.objects.filter(pk=album.pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AlbumKeepsPagination(KeepFeedPagination):
    # Oldest memory first, so an album reads like the story of the trip.
    ordering = ALBUM_KEEP_ORDERING


class AlbumKeepsView(generics.ListAPIView):
    """An album's posts in feed shape, oldest memory first."""

    serializer_class = KeepFeedSerializer
    pagination_class = AlbumKeepsPagination

    def get_queryset(self):
        # Avoid queryset evaluation during schema generation
        if getattr(self, "swagger_fake_view", False):
            return Keep.objects.none()
        user = self.request.user
        album_id = self.kwargs["album_id"]
        if not Album.objects.filter(pk=album_id, circle__memberships__user=user).exists():
            raise Http404
        # Built on the feed, so a post shows here exactly when it shows there.
        return feed_queryset(user).filter(album_memberships__album_id=album_id)

    @extend_schema(
        summary="Album posts",
        description="The album's posts in the same shape as the feed, oldest memory first. Only posts the feed "
        "would show are listed. Cursor-paginated: follow `next`. 404 unless the user belongs to its circle.",
        parameters=[
            OpenApiParameter(
                name="page_size",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Posts per page (default 10, max 30)",
            ),
        ],
        responses={
            200: OpenApiResponse(response=KeepFeedSerializer(many=True), description="A page of posts"),
            404: OpenApiResponse(description="Not found or not visible to the user"),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AlbumKeepView(APIView):
    """Add (POST) or remove (DELETE) a post. Any circle member may; both are idempotent."""

    @extend_schema(
        summary="Add a post to an album",
        description="Any member of the circle can add one of its posts. Adding it again is a no-op.",
        request=None,
        responses={
            200: OpenApiResponse(description="`{in_album: true}`, already in the album"),
            201: OpenApiResponse(description="`{in_album: true}`, newly added"),
            400: OpenApiResponse(description="The post is from another circle"),
            404: OpenApiResponse(description="Album or post not found or not visible to the user"),
        },
    )
    def post(self, request, album_id, keep_id):
        album = get_object_or_404(Album, pk=album_id, circle__memberships__user=request.user)
        keep = get_visible_keep_or_404(request.user, keep_id)
        if keep.circle_id != album.circle_id:
            raise ValidationError({"keep": "Only posts from the album's circle can be added."})
        _, created = AlbumKeep.objects.get_or_create(album=album, keep=keep, defaults={"added_by": request.user})
        if created:
            album.touch()
        return Response({"in_album": True}, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @extend_schema(
        summary="Remove a post from an album",
        description="Any member of the circle can remove a post; the post itself stays. Removing one that isn't "
        "in the album is a no-op.",
        request=None,
        responses={
            204: OpenApiResponse(description="Not in the album (any more)"),
            404: OpenApiResponse(description="Album not found or not visible to the user"),
        },
    )
    def delete(self, request, album_id, keep_id):
        album = get_object_or_404(Album, pk=album_id, circle__memberships__user=request.user)
        deleted, _ = AlbumKeep.objects.filter(album=album, keep_id=keep_id).delete()
        if deleted:
            if album.cover_keep_id == keep_id:
                Album.objects.filter(pk=album.pk).update(cover_keep=None)
            album.touch()
        return Response(status=status.HTTP_204_NO_CONTENT)
