"""Circle admins list their circle's children and set their birthdates (used by the Birthdays album)."""

from __future__ import annotations

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import OpenApiResponse, OpenApiTypes, extend_schema
from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView

from mysite.albums.birthdays import queue_sync as queue_birthday_album_sync
from mysite.auth.permissions import IsEmailVerified
from mysite.notification_utils import success_response

from ..models import ChildProfile, Circle, CircleMembership, UserRole
from ..serializers import ChildBirthdateSerializer


def require_circle_admin(user, circle_id):
    if user.is_superuser:
        return
    if not CircleMembership.objects.filter(circle_id=circle_id, user=user, role=UserRole.CIRCLE_ADMIN).exists():
        raise PermissionDenied(_("Only circle admins can manage children"))


class CircleChildListView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsEmailVerified]
    serializer_class = ChildBirthdateSerializer

    @extend_schema(
        description="The circle's child profiles with their birthdates, in name order. Circle admins only.",
        responses={200: OpenApiResponse(response=OpenApiTypes.OBJECT, description="`{children: [...]}`")},
    )
    def get(self, request, circle_id):
        circle = get_object_or_404(Circle, id=circle_id)
        require_circle_admin(request.user, circle.id)
        children = circle.children.order_by("display_name", "id")
        return success_response({"children": ChildBirthdateSerializer(children, many=True).data})


class ChildBirthdateView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsEmailVerified]
    serializer_class = ChildBirthdateSerializer

    @extend_schema(
        description="Set or clear a child's birthdate (not in the future). Circle admins only. When the circle "
        "has the Birthdays album on, it is updated in the background.",
        request=ChildBirthdateSerializer,
        responses={200: OpenApiResponse(response=OpenApiTypes.OBJECT, description="`{child: {...}}`")},
    )
    def patch(self, request, child_id):
        child = get_object_or_404(ChildProfile.objects.select_related("circle"), id=child_id)
        require_circle_admin(request.user, child.circle_id)
        serializer = ChildBirthdateSerializer(child, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            serializer.save()
            if child.circle.birthday_album_enabled and child.birthdate:
                queue_birthday_album_sync(child.circle_id)
        return success_response({"child": serializer.data})
