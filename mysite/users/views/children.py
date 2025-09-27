"""Child profile upgrade workflow views."""
from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiResponse, OpenApiTypes, extend_schema

from ..models import (
    ChildGuardianConsent,
    ChildProfile,
    ChildProfileUpgradeStatus,
    ChildUpgradeEventType,
    CircleMembership,
    User,
    UserRole,
)
from ..serializers import (
    ChildProfileUpgradeConfirmSerializer,
    ChildProfileUpgradeRequestSerializer,
    CircleSerializer,
    UserSerializer,
)
from ..tasks import CHILD_UPGRADE_TEMPLATE, send_email_task
from ..token_utils import delete_token, pop_token, store_token
from .utils import TOKEN_TTL_SECONDS, _get_tokens_for_user


class ChildProfileUpgradeRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChildProfileUpgradeRequestSerializer

    @extend_schema(
        description='Trigger the guardian consent workflow to promote a child profile to a full account.',
        request=ChildProfileUpgradeRequestSerializer,
        responses={
            202: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description='Upgrade invitation issued successfully.',
            ),
            400: OpenApiResponse(description='Validation error'),
        },
    )
    def post(self, request, child_id):
        child = get_object_or_404(ChildProfile, id=child_id)
        membership = CircleMembership.objects.filter(circle=child.circle, user=request.user).first()
        if not membership or membership.role != UserRole.CIRCLE_ADMIN:
            raise PermissionDenied(_('Only circle admins can upgrade child profiles'))

        serializer = ChildProfileUpgradeRequestSerializer(data=request.data, context={'child': child})
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            previous_token = child.upgrade_token
            if previous_token:
                delete_token('child-upgrade', previous_token)
            child.pending_invite_email = serializer.validated_data['email']
            child.upgrade_status = ChildProfileUpgradeStatus.PENDING
            child.upgrade_requested_by = request.user

            ttl = TOKEN_TTL_SECONDS
            expires_at = timezone.now() + timedelta(seconds=ttl) if ttl else None
            token = store_token(
                'child-upgrade',
                {
                    'child_id': str(child.id),
                    'circle_id': child.circle_id,
                    'email': child.pending_invite_email,
                    'issued_at': timezone.now().isoformat(),
                },
                ttl=TOKEN_TTL_SECONDS,
            )
            child.upgrade_token = token
            child.upgrade_token_expires_at = expires_at
            child.save(
                update_fields=[
                    'pending_invite_email',
                    'upgrade_status',
                    'upgrade_requested_by',
                    'upgrade_token',
                    'upgrade_token_expires_at',
                    'updated_at',
                ]
            )

            consent = ChildGuardianConsent.objects.create(
                child=child,
                guardian_name=serializer.validated_data['guardian_name'],
                guardian_relationship=serializer.validated_data['guardian_relationship'],
                agreement_reference=serializer.validated_data.get('agreement_reference', ''),
                consent_method=serializer.validated_data['consent_method'],
                consent_metadata=serializer.validated_data.get('consent_metadata', {}),
                captured_by=request.user,
            )

            if previous_token:
                child.log_upgrade_event(
                    ChildUpgradeEventType.TOKEN_REISSUED,
                    performed_by=request.user,
                    metadata={'old_token': previous_token, 'new_token': token},
                )

            child.log_upgrade_event(
                ChildUpgradeEventType.REQUEST_INITIATED,
                performed_by=request.user,
                metadata={
                    'email': child.pending_invite_email,
                    'token': token,
                    'consent_id': str(consent.id),
                    'consent_method': consent.consent_method,
                },
            )

        send_email_task.delay(
            to_email=child.pending_invite_email,
            template_id=CHILD_UPGRADE_TEMPLATE,
            context={
                'token': token,
                'email': child.pending_invite_email,
                'child_name': child.display_name,
                'circle_name': child.circle.name,
            },
        )
        return Response({'message': _('Upgrade invitation created'), 'token': token}, status=status.HTTP_202_ACCEPTED)


class ChildProfileUpgradeConfirmView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ChildProfileUpgradeConfirmSerializer

    @extend_schema(
        description='Confirm a child profile upgrade using the guardian-issued token.',
        request=ChildProfileUpgradeConfirmSerializer,
        responses={
            201: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description='Account created and linked successfully.',
            ),
            400: OpenApiResponse(description='Invalid or expired token'),
        },
    )
    def post(self, request):
        serializer = ChildProfileUpgradeConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = pop_token('child-upgrade', serializer.validated_data['token'])
        if not payload:
            return Response({'detail': _('Invalid or expired token')}, status=status.HTTP_400_BAD_REQUEST)

        child = ChildProfile.objects.filter(id=payload['child_id']).select_related('circle').first()
        if not child:
            return Response({'detail': _('Child profile not found')}, status=status.HTTP_404_NOT_FOUND)
        if child.linked_user:
            return Response({'detail': _('Child profile already linked')}, status=status.HTTP_400_BAD_REQUEST)
        if not child.upgrade_token:
            return Response({'detail': _('Upgrade invitation has been revoked. Please request a new invitation.')}, status=status.HTTP_400_BAD_REQUEST)
        provided_token = serializer.validated_data['token']
        if child.upgrade_token != provided_token:
            return Response({'detail': _('Upgrade invitation mismatch. Please request a new invitation.')}, status=status.HTTP_400_BAD_REQUEST)
        if child.upgrade_token_expires_at and timezone.now() > child.upgrade_token_expires_at:
            return Response({'detail': _('Upgrade invitation expired. Please request a new invitation.')}, status=status.HTTP_400_BAD_REQUEST)

        email = payload['email']
        password = serializer.validated_data['password']
        username = serializer.validated_data['username']

        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                role=UserRole.CIRCLE_MEMBER,
            )
            user.email_verified = True
            user.save(update_fields=['email_verified'])

            CircleMembership.objects.create(user=user, circle=child.circle, role=UserRole.CIRCLE_MEMBER)
            child.linked_user = user
            child.upgrade_status = ChildProfileUpgradeStatus.LINKED
            child.pending_invite_email = None
            child.upgrade_token = None
            child.upgrade_token_expires_at = None
            child.upgrade_requested_by = None
            child.save(
                update_fields=[
                    'linked_user',
                    'upgrade_status',
                    'pending_invite_email',
                    'upgrade_token',
                    'upgrade_token_expires_at',
                    'upgrade_requested_by',
                    'updated_at',
                ]
            )

            child.log_upgrade_event(
                ChildUpgradeEventType.UPGRADE_COMPLETED,
                performed_by=user,
                metadata={'email': email, 'user_id': user.id},
            )

        return Response(
            {
                'detail': _('Account created'),
                'user': UserSerializer(user).data,
                'tokens': _get_tokens_for_user(user),
            },
            status=status.HTTP_201_CREATED,
        )
