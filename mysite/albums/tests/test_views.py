"""Tests for the albums API."""

from datetime import timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework import status

from mysite.albums.models import Album, AlbumKeep
from mysite.circles.models import Circle
from mysite.keeps.models import KeepFavorite

from .helpers import BASE_TIME, make_album, make_keep

ALBUMS_URL = "/api/albums/"


def album_url(album_id):
    return f"{ALBUMS_URL}{album_id}/"


def album_keeps_url(album_id):
    return f"{ALBUMS_URL}{album_id}/keeps/"


def album_keep_url(album_id, keep_id):
    return f"{ALBUMS_URL}{album_id}/keeps/{keep_id}/"


def names(response):
    return [item["name"] for item in response.data["results"]]


def titles(response):
    return [item["title"] for item in response.data["results"]]


def error_fields(response):
    """Fields named in the project's validation error envelope."""
    return {message["context"]["field"] for message in response.data["messages"]}


@pytest.mark.django_db
class TestAuthentication:
    def test_every_endpoint_requires_authentication(self, api_client, circle, admin):
        keep = make_keep(circle, admin)
        album = make_album(circle, admin)

        assert api_client.get(ALBUMS_URL).status_code == status.HTTP_401_UNAUTHORIZED
        assert api_client.post(ALBUMS_URL, {}).status_code == status.HTTP_401_UNAUTHORIZED
        assert api_client.get(album_url(album.id)).status_code == status.HTTP_401_UNAUTHORIZED
        assert api_client.patch(album_url(album.id), {}).status_code == status.HTTP_401_UNAUTHORIZED
        assert api_client.delete(album_url(album.id)).status_code == status.HTTP_401_UNAUTHORIZED
        assert api_client.get(album_keeps_url(album.id)).status_code == status.HTTP_401_UNAUTHORIZED
        assert api_client.post(album_keep_url(album.id, keep.id)).status_code == status.HTTP_401_UNAUTHORIZED
        assert api_client.delete(album_keep_url(album.id, keep.id)).status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestAlbumList:
    def test_lists_albums_from_the_users_circles_only(self, api_client, circle, other_circle, admin, outsider):
        make_album(circle, admin, name="Ours")
        make_album(other_circle, outsider, name="Theirs")
        api_client.force_authenticate(user=admin)

        response = api_client.get(ALBUMS_URL)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert names(response) == ["Ours"]
        assert response.data["results"][0]["circle"] == {"id": circle.id, "name": circle.name, "slug": circle.slug}

    def test_most_recently_changed_first_and_adding_a_post_bumps(self, api_client, circle, admin):
        older = make_album(circle, admin, name="Older")
        make_album(circle, admin, name="Newer")
        api_client.force_authenticate(user=admin)
        assert names(api_client.get(ALBUMS_URL)) == ["Newer", "Older"]

        api_client.post(album_keep_url(older.id, make_keep(circle, admin).id))

        assert names(api_client.get(ALBUMS_URL)) == ["Older", "Newer"]

    def test_filters_by_circle(self, api_client, circle, admin):
        second = Circle.objects.create(name="Second Family", created_by=admin)
        make_album(circle, admin, name="First")
        make_album(second, admin, name="Second")
        api_client.force_authenticate(user=admin)

        assert names(api_client.get(ALBUMS_URL, {"circle_slug": second.slug})) == ["Second"]

    def test_post_count_and_default_cover(self, api_client, circle, admin):
        text_post = make_keep(circle, admin, BASE_TIME - timedelta(days=3), media=())
        processing = make_keep(circle, admin, BASE_TIME - timedelta(days=2), media=(("video", False),))
        first_photo = make_keep(circle, admin, BASE_TIME - timedelta(days=1), media=(("photo", False), ("photo", True)))
        later_photo = make_keep(circle, admin, BASE_TIME)
        make_album(circle, admin, keeps=[later_photo, processing, text_post, first_photo])
        api_client.force_authenticate(user=admin)

        album = api_client.get(ALBUMS_URL).data["results"][0]

        # The still-processing video isn't shown anywhere, so it isn't counted.
        assert album["post_count"] == 3
        # The oldest post with a displayable photo; its first photo has no thumbnails yet.
        assert album["cover"] == {
            "keep_id": str(first_photo.id),
            "media_type": "photo",
            "url": f"https://cdn.test/original/{first_photo.id}-0",
        }

    def test_video_cover_uses_its_poster_frame(self, api_client, circle, admin):
        video = make_keep(circle, admin, media=(("video", True),))
        make_album(circle, admin, keeps=[video])
        api_client.force_authenticate(user=admin)

        cover = api_client.get(ALBUMS_URL).data["results"][0]["cover"]

        assert cover == {
            "keep_id": str(video.id),
            "media_type": "video",
            "url": f"https://cdn.test/gallery/{video.id}-0",
        }

    def test_empty_album_has_no_cover(self, api_client, circle, admin):
        make_album(circle, admin, keeps=[make_keep(circle, admin, media=())])
        api_client.force_authenticate(user=admin)

        album = api_client.get(ALBUMS_URL).data["results"][0]

        assert album["cover"] is None
        assert album["post_count"] == 1

    def test_chosen_cover_wins_while_in_the_album(self, api_client, circle, admin):
        first = make_keep(circle, admin, BASE_TIME - timedelta(days=1))
        chosen = make_keep(circle, admin, BASE_TIME)
        album = make_album(circle, admin, keeps=[first, chosen])
        Album.objects.filter(pk=album.pk).update(cover_keep=chosen)
        api_client.force_authenticate(user=admin)

        assert api_client.get(ALBUMS_URL).data["results"][0]["cover"]["keep_id"] == str(chosen.id)

        api_client.delete(album_keep_url(album.id, chosen.id))

        album.refresh_from_db()
        assert album.cover_keep is None
        assert api_client.get(ALBUMS_URL).data["results"][0]["cover"]["keep_id"] == str(first.id)

    def test_can_edit_for_creator_and_admin_only(self, api_client, circle, admin, member, other_member):
        make_album(circle, member, name="Member's")
        make_album(circle, admin, name="Admin's")

        def can_edit(user):
            api_client.force_authenticate(user=user)
            return {item["name"]: item["can_edit"] for item in api_client.get(ALBUMS_URL).data["results"]}

        assert can_edit(admin) == {"Member's": True, "Admin's": True}
        assert can_edit(member) == {"Member's": True, "Admin's": False}
        assert can_edit(other_member) == {"Member's": False, "Admin's": False}

    def test_keep_filter_flags_the_albums_holding_it(self, api_client, circle, admin):
        second = Circle.objects.create(name="Second Family", created_by=admin)
        keep = make_keep(circle, admin)
        make_album(circle, admin, name="Has it", keeps=[keep])
        make_album(circle, admin, name="Doesn't")
        make_album(second, admin, name="Other circle")
        api_client.force_authenticate(user=admin)

        response = api_client.get(ALBUMS_URL, {"keep": str(keep.id)})

        assert {item["name"]: item["has_keep"] for item in response.data["results"]} == {
            "Has it": True,
            "Doesn't": False,
        }
        assert all(item["has_keep"] is None for item in api_client.get(ALBUMS_URL).data["results"])

    def test_keep_filter_404s_for_a_keep_the_user_cannot_see(self, api_client, circle, other_circle, admin, outsider):
        foreign = make_keep(other_circle, outsider)
        api_client.force_authenticate(user=admin)

        assert api_client.get(ALBUMS_URL, {"keep": str(foreign.id)}).status_code == status.HTTP_404_NOT_FOUND
        assert api_client.get(ALBUMS_URL, {"keep": "not-a-uuid"}).status_code == status.HTTP_404_NOT_FOUND

    def test_limit_offset_pagination(self, api_client, circle, admin):
        for n in range(5):
            album = make_album(circle, admin, name=f"Album {n}")
            Album.objects.filter(pk=album.pk).update(updated_at=BASE_TIME + timedelta(minutes=n))
        api_client.force_authenticate(user=admin)

        first = api_client.get(ALBUMS_URL, {"limit": 3})
        second = api_client.get(first.data["next"])

        assert first.data["count"] == 5
        assert names(first) == ["Album 4", "Album 3", "Album 2"]
        assert names(second) == ["Album 1", "Album 0"]
        assert second.data["next"] is None

    def test_query_count_does_not_grow_with_albums(self, api_client, circle, admin):
        api_client.force_authenticate(user=admin)
        make_album(circle, admin, keeps=[make_keep(circle, admin)])
        with CaptureQueriesContext(connection) as small:
            api_client.get(ALBUMS_URL)

        for n in range(5):
            make_album(circle, admin, name=f"More {n}", keeps=[make_keep(circle, admin), make_keep(circle, admin)])
        with CaptureQueriesContext(connection) as large:
            api_client.get(ALBUMS_URL)

        assert len(large.captured_queries) == len(small.captured_queries)


@pytest.mark.django_db
class TestAlbumCreate:
    def test_any_member_can_create(self, api_client, circle, member):
        api_client.force_authenticate(user=member)

        response = api_client.post(ALBUMS_URL, {"circle": circle.id, "name": "  Beach trip 2026  "}, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "Beach trip 2026"
        assert response.data["created_by"] == member.id
        assert response.data["post_count"] == 0
        assert response.data["can_edit"] is True
        assert Album.objects.get().created_by == member

    def test_with_a_first_post(self, api_client, circle, admin, member):
        keep = make_keep(circle, admin)
        api_client.force_authenticate(user=member)

        response = api_client.post(ALBUMS_URL, {"circle": circle.id, "name": "Beach", "keep": str(keep.id)})

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["post_count"] == 1
        assert response.data["cover"]["keep_id"] == str(keep.id)
        assert AlbumKeep.objects.get().added_by == member

    def test_rejects_a_circle_the_user_is_not_in(self, api_client, other_circle, admin):
        api_client.force_authenticate(user=admin)

        response = api_client.post(ALBUMS_URL, {"circle": other_circle.id, "name": "Sneaky"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "circle" in error_fields(response)
        assert not Album.objects.exists()

    def test_rejects_a_first_post_from_another_circle(self, api_client, circle, admin):
        second = Circle.objects.create(name="Second Family", created_by=admin)
        keep = make_keep(second, admin)
        api_client.force_authenticate(user=admin)

        response = api_client.post(ALBUMS_URL, {"circle": circle.id, "name": "Mixed", "keep": str(keep.id)})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "keep" in error_fields(response)
        assert not Album.objects.exists()

    def test_requires_a_name(self, api_client, circle, admin):
        api_client.force_authenticate(user=admin)

        response = api_client.post(ALBUMS_URL, {"circle": circle.id, "name": "   "})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "name" in error_fields(response)


@pytest.mark.django_db
class TestAlbumDetail:
    def test_member_sees_it(self, api_client, circle, admin, member):
        album = make_album(circle, admin, keeps=[make_keep(circle, admin)])
        api_client.force_authenticate(user=member)

        response = api_client.get(album_url(album.id))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == album.name
        assert response.data["post_count"] == 1
        assert response.data["can_edit"] is False

    def test_404_outside_the_circle(self, api_client, circle, admin, outsider):
        album = make_album(circle, admin)
        api_client.force_authenticate(user=outsider)

        assert api_client.get(album_url(album.id)).status_code == status.HTTP_404_NOT_FOUND
        assert api_client.patch(album_url(album.id), {"name": "x"}).status_code == status.HTTP_404_NOT_FOUND
        assert api_client.delete(album_url(album.id)).status_code == status.HTTP_404_NOT_FOUND

    def test_creator_renames(self, api_client, circle, member):
        album = make_album(circle, member)
        api_client.force_authenticate(user=member)

        response = api_client.patch(album_url(album.id), {"name": "Lake trip", "description": "July"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert (response.data["name"], response.data["description"]) == ("Lake trip", "July")
        album.refresh_from_db()
        assert album.name == "Lake trip"

    def test_circle_admin_renames_someone_elses(self, api_client, circle, admin, member):
        album = make_album(circle, member)
        api_client.force_authenticate(user=admin)

        assert api_client.patch(album_url(album.id), {"name": "Admin's pick"}).status_code == status.HTTP_200_OK

    def test_other_members_cannot_rename_or_delete(self, api_client, circle, member, other_member):
        album = make_album(circle, member)
        api_client.force_authenticate(user=other_member)

        assert api_client.patch(album_url(album.id), {"name": "Mine now"}).status_code == status.HTTP_403_FORBIDDEN
        assert api_client.delete(album_url(album.id)).status_code == status.HTTP_403_FORBIDDEN
        album.refresh_from_db()
        assert album.name == "Beach trip 2026"

    def test_cover_must_be_a_post_in_the_album(self, api_client, circle, admin):
        inside = make_keep(circle, admin)
        outside = make_keep(circle, admin)
        album = make_album(circle, admin, keeps=[inside])
        api_client.force_authenticate(user=admin)

        rejected = api_client.patch(album_url(album.id), {"cover_keep": str(outside.id)}, format="json")
        accepted = api_client.patch(album_url(album.id), {"cover_keep": str(inside.id)}, format="json")
        cleared = api_client.patch(album_url(album.id), {"cover_keep": None}, format="json")

        assert rejected.status_code == status.HTTP_400_BAD_REQUEST
        assert accepted.status_code == status.HTTP_200_OK
        assert accepted.data["cover_keep"] == inside.id
        assert cleared.data["cover_keep"] is None

    def test_creator_or_admin_deletes_it_and_posts_stay(self, api_client, circle, admin, member):
        keep = make_keep(circle, admin)
        mine = make_album(circle, member, keeps=[keep])
        theirs = make_album(circle, member, name="Second", keeps=[keep])

        api_client.force_authenticate(user=member)
        assert api_client.delete(album_url(mine.id)).status_code == status.HTTP_204_NO_CONTENT
        api_client.force_authenticate(user=admin)
        assert api_client.delete(album_url(theirs.id)).status_code == status.HTTP_204_NO_CONTENT

        assert not Album.objects.exists()
        keep.refresh_from_db()


@pytest.mark.django_db
class TestAlbumKeeps:
    def test_lists_posts_oldest_memory_first_in_feed_shape(self, api_client, circle, admin, member):
        later = make_keep(circle, admin, BASE_TIME, title="Later")
        earlier = make_keep(circle, admin, BASE_TIME - timedelta(days=1), title="Earlier")
        make_keep(circle, admin, BASE_TIME, title="Not in the album")
        album = make_album(circle, admin, keeps=[later, earlier])
        KeepFavorite.objects.create(user=member, keep=later)
        api_client.force_authenticate(user=member)

        response = api_client.get(album_keeps_url(album.id))

        assert response.status_code == status.HTTP_200_OK
        assert titles(response) == ["Earlier", "Later"]
        first = response.data["results"][0]
        assert first["circle"]["slug"] == circle.slug
        assert first["media"][0]["url"] == f"https://cdn.test/gallery/{earlier.id}-0"
        assert [item["favorited"] for item in response.data["results"]] == [False, True]

    def test_hides_posts_the_feed_hides(self, api_client, circle, admin):
        shown = make_keep(circle, admin, title="Shown")
        processing = make_keep(circle, admin, media=(("video", False),), title="Processing")
        album = make_album(circle, admin, keeps=[shown, processing])
        api_client.force_authenticate(user=admin)

        assert titles(api_client.get(album_keeps_url(album.id))) == ["Shown"]

    def test_cursor_pagination(self, api_client, circle, admin):
        keeps = [make_keep(circle, admin, BASE_TIME + timedelta(days=n), title=f"Keep {n}") for n in range(5)]
        album = make_album(circle, admin, keeps=keeps)
        api_client.force_authenticate(user=admin)

        first = api_client.get(album_keeps_url(album.id), {"page_size": 3})
        second = api_client.get(first.data["next"])

        assert titles(first) == ["Keep 0", "Keep 1", "Keep 2"]
        assert titles(second) == ["Keep 3", "Keep 4"]
        assert second.data["next"] is None

    def test_404_outside_the_circle(self, api_client, circle, admin, outsider):
        album = make_album(circle, admin, keeps=[make_keep(circle, admin)])
        api_client.force_authenticate(user=outsider)

        assert api_client.get(album_keeps_url(album.id)).status_code == status.HTTP_404_NOT_FOUND

    def test_query_count_does_not_grow_with_posts(self, api_client, circle, admin):
        album = make_album(circle, admin, keeps=[make_keep(circle, admin)])
        api_client.force_authenticate(user=admin)
        with CaptureQueriesContext(connection) as small:
            api_client.get(album_keeps_url(album.id))

        for n in range(5):
            AlbumKeep.objects.create(album=album, keep=make_keep(circle, admin, title=f"More {n}"))
        with CaptureQueriesContext(connection) as large:
            api_client.get(album_keeps_url(album.id))

        assert len(large.captured_queries) == len(small.captured_queries)


@pytest.mark.django_db
class TestAddRemoveKeep:
    def test_any_member_adds_once(self, api_client, circle, admin, member):
        keep = make_keep(circle, admin)
        album = make_album(circle, admin)
        api_client.force_authenticate(user=member)

        first = api_client.post(album_keep_url(album.id, keep.id))
        again = api_client.post(album_keep_url(album.id, keep.id))

        assert first.status_code == status.HTTP_201_CREATED
        assert first.data == {"in_album": True}
        assert again.status_code == status.HTTP_200_OK
        entry = AlbumKeep.objects.get()
        assert (entry.album, entry.keep, entry.added_by) == (album, keep, member)

    def test_rejects_a_post_from_another_of_the_users_circles(self, api_client, circle, admin):
        second = Circle.objects.create(name="Second Family", created_by=admin)
        album = make_album(circle, admin)
        api_client.force_authenticate(user=admin)

        response = api_client.post(album_keep_url(album.id, make_keep(second, admin).id))

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not AlbumKeep.objects.exists()

    def test_404_for_an_album_or_post_the_user_cannot_see(self, api_client, circle, other_circle, admin, outsider):
        album = make_album(circle, admin)
        keep = make_keep(circle, admin)
        foreign_keep = make_keep(other_circle, outsider)
        foreign_album = make_album(other_circle, outsider)
        api_client.force_authenticate(user=admin)

        assert api_client.post(album_keep_url(album.id, foreign_keep.id)).status_code == status.HTTP_404_NOT_FOUND
        assert api_client.post(album_keep_url(foreign_album.id, keep.id)).status_code == status.HTTP_404_NOT_FOUND
        assert api_client.delete(album_keep_url(foreign_album.id, keep.id)).status_code == status.HTTP_404_NOT_FOUND
        assert not AlbumKeep.objects.exists()

    def test_any_member_removes_and_it_is_idempotent(self, api_client, circle, admin, member):
        keep = make_keep(circle, admin)
        album = make_album(circle, admin, keeps=[keep])
        api_client.force_authenticate(user=member)

        assert api_client.delete(album_keep_url(album.id, keep.id)).status_code == status.HTTP_204_NO_CONTENT
        assert api_client.delete(album_keep_url(album.id, keep.id)).status_code == status.HTTP_204_NO_CONTENT
        assert not AlbumKeep.objects.exists()
        keep.refresh_from_db()
