import os
import uuid

from django.core.cache import cache
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import (
    ChildProfile,
    ChildProfileUpgradeStatus,
    Circle,
    CircleInvitation,
    CircleInvitationStatus,
    CircleMembership,
    User,
    UserNotificationPreferences,
    UserRole,
)
from .tasks import (
    CIRCLE_INVITATION_TEMPLATE,
    CHILD_UPGRADE_TEMPLATE,
    EMAIL_VERIFICATION_TEMPLATE,
    PASSWORD_RESET_TEMPLATE,
    send_email_task,
)

from .serializers import (
    ChildProfileUpgradeConfirmSerializer,
    ChildProfileUpgradeRequestSerializer,
    CircleInvitationAcceptSerializer,
    CircleInvitationCreateSerializer,
    CircleInvitationResponseSerializer,
    CircleInvitationSerializer,
    CircleCreateSerializer,
    CircleMemberAddSerializer,
    CircleMemberSerializer,
    CircleMembershipSerializer,
    CircleSerializer,
    EmailPreferencesSerializer,
    EmailVerificationConfirmSerializer,
    EmailVerificationSerializer,
    LoginSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    SignupSerializer,
    UserProfileSerializer,
    UserSerializer,
)

TOKEN_TTL_SECONDS = int(os.environ.get('AUTH_TOKEN_TTL', 900))


def _token_cache_key(prefix: str, token: str) -> str:
    return f"auth:{prefix}:{token}"


def _store_token(prefix: str, payload: dict, ttl: int | None = None) -> str:
    token = uuid.uuid4().hex
    cache.set(_token_cache_key(prefix, token), payload, ttl or TOKEN_TTL_SECONDS)
    return token


def _pop_token(prefix: str, token: str):
    key = _token_cache_key(prefix, token)
    payload = cache.get(key)
    if payload is not None:
        cache.delete(key)
    return payload


def _get_tokens_for_user(user: User) -> dict:
    refresh = RefreshToken.for_user(user)
    return {'refresh': str(refresh), 'access': str(refresh.access_token)}


class SignupView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, circle = serializer.save()

        verification_token = _store_token(
            'verify-email',
            {'user_id': user.id, 'issued_at': timezone.now().isoformat()},
        )

        send_email_task.delay(
            to_email=user.email,
            template_id=EMAIL_VERIFICATION_TEMPLATE,
            context={
                'token': verification_token,
                'email': user.email,
                'username': user.username,
            },
        )

        data = serializer.to_representation((user, circle))
        data['tokens'] = _get_tokens_for_user(user)
        data['verification_token'] = verification_token
        return Response(data, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        data = {
            'user': UserSerializer(user).data,
            'tokens': _get_tokens_for_user(user),
        }
        return Response(data)


class EmailVerificationResendView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = EmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token = _store_token(
            'verify-email',
            {'user_id': user.id, 'issued_at': timezone.now().isoformat()},
        )
        send_email_task.delay(
            to_email=user.email,
            template_id=EMAIL_VERIFICATION_TEMPLATE,
            context={
                'token': token,
                'email': user.email,
                'username': user.username,
            },
        )
        return Response({'message': _('Verification email reissued'), 'token': token}, status=status.HTTP_202_ACCEPTED)


class EmailVerificationConfirmView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = EmailVerificationConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = _pop_token('verify-email', serializer.validated_data['token'])
        if not payload:
            return Response({'detail': _('Invalid or expired token')}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.filter(id=payload['user_id']).first()
        if not user:
            return Response({'detail': _('User not found')}, status=status.HTTP_404_NOT_FOUND)
        if not user.email_verified:
            user.email_verified = True
            user.save(update_fields=['email_verified'])
        return Response({'detail': _('Email verified successfully')})


class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        if user:
            token = _store_token(
                'password-reset',
                {'user_id': user.id, 'issued_at': timezone.now().isoformat()},
            )
            send_email_task.delay(
                to_email=user.email,
                template_id=PASSWORD_RESET_TEMPLATE,
                context={
                    'token': token,
                    'email': user.email,
                    'username': user.username,
                },
            )
            return Response({'message': _('Password reset sent'), 'token': token}, status=status.HTTP_202_ACCEPTED)
        return Response({'message': _('Password reset sent')}, status=status.HTTP_202_ACCEPTED)


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = _pop_token('password-reset', serializer.validated_data['token'])
        if not payload:
            return Response({'detail': _('Invalid or expired token')}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.filter(id=payload['user_id']).first()
        if not user:
            return Response({'detail': _('User not found')}, status=status.HTTP_404_NOT_FOUND)
        user.set_password(serializer.validated_data['password'])
        user.save(update_fields=['password'])
        return Response({'detail': _('Password updated')})


class PasswordChangeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data['password'])
        user.save(update_fields=['password'])
        return Response({'detail': _('Password changed'), 'tokens': _get_tokens_for_user(user)})


class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response({'user': serializer.data})

    def patch(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'user': serializer.data})


class EmailPreferencesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, request):
        circle_id = request.query_params.get('circle_id')
        circle = None
        if circle_id:
            circle = get_object_or_404(Circle, id=circle_id)
            if not CircleMembership.objects.filter(circle=circle, user=request.user).exists():
                raise PermissionDenied(_('Not a member of this circle'))
        prefs, _ = UserNotificationPreferences.objects.get_or_create(user=request.user, circle=circle)
        return prefs

    def get(self, request):
        prefs = self.get_object(request)
        return Response(EmailPreferencesSerializer(prefs).data)

    def patch(self, request):
        prefs = self.get_object(request)
        serializer = EmailPreferencesSerializer(prefs, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class UserCircleListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        memberships = (
            CircleMembership.objects.filter(user=request.user)
            .select_related('circle')
            .order_by('circle__name')
        )
        serializer = CircleMembershipSerializer(memberships, many=True)
        return Response({'circles': serializer.data})

    def post(self, request):
        serializer = CircleCreateSerializer(data=request.data, context={'user': request.user})
        serializer.is_valid(raise_exception=True)
        circle = serializer.save()
        return Response({'circle': CircleSerializer(circle).data}, status=status.HTTP_201_CREATED)


class CircleDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, circle_id):
        circle = get_object_or_404(Circle, id=circle_id)
        membership = CircleMembership.objects.filter(circle=circle, user=request.user).first()
        if not (request.user.is_superuser or (membership and membership.role == UserRole.CIRCLE_ADMIN)):
            raise PermissionDenied(_('Only circle admins can update circle details'))

        serializer = CircleCreateSerializer(circle, data=request.data, partial=True, context={'user': request.user})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'circle': CircleSerializer(circle).data})


class CircleInvitationCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, circle_id):
        circle = get_object_or_404(Circle, id=circle_id)
        membership = CircleMembership.objects.filter(circle=circle, user=request.user).first()
        if not membership or membership.role != UserRole.CIRCLE_ADMIN:
            raise PermissionDenied(_('Only circle admins can invite members'))

        serializer = CircleInvitationCreateSerializer(data=request.data, context={'circle': circle})
        serializer.is_valid(raise_exception=True)

        invitation = CircleInvitation.objects.create(
            circle=circle,
            email=serializer.validated_data['email'],
            invited_by=request.user,
            role=serializer.validated_data['role'],
        )

        token = _store_token(
            'circle-invite',
            {
                'invitation_id': str(invitation.id),
                'circle_id': circle.id,
                'email': invitation.email,
                'role': invitation.role,
                'issued_at': timezone.now().isoformat(),
            },
        )

        send_email_task.delay(
            to_email=invitation.email,
            template_id=CIRCLE_INVITATION_TEMPLATE,
            context={
                'token': token,
                'email': invitation.email,
                'circle_name': circle.name,
                'invited_by': request.user.username,
            },
        )

        data = CircleInvitationSerializer(invitation).data
        data['token'] = token
        return Response({'invitation': data}, status=status.HTTP_202_ACCEPTED)


class CircleInvitationListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        invitations = CircleInvitation.objects.filter(
            email__iexact=request.user.email,
            status=CircleInvitationStatus.PENDING,
        ).select_related('circle')
        data = CircleInvitationSerializer(invitations, many=True).data
        return Response({'invitations': data})


class CircleMemberListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, circle_id):
        circle = get_object_or_404(Circle, id=circle_id)
        membership = CircleMembership.objects.filter(circle=circle, user=request.user).first()
        if not (request.user.is_superuser or (membership and membership.role == UserRole.CIRCLE_ADMIN)):
            raise PermissionDenied(_('Only circle admins can view members'))

        memberships = CircleMembership.objects.filter(circle=circle).select_related('user').order_by('user__username')
        serializer = CircleMemberSerializer(memberships, many=True)
        return Response({'circle': CircleSerializer(circle).data, 'members': serializer.data})

    def post(self, request, circle_id):
        circle = get_object_or_404(Circle, id=circle_id)
        membership = CircleMembership.objects.filter(circle=circle, user=request.user).first()
        if not (request.user.is_superuser or (membership and membership.role == UserRole.CIRCLE_ADMIN)):
            raise PermissionDenied(_('Only circle admins can add members'))

        serializer = CircleMemberAddSerializer(
            data=request.data,
            context={'circle': circle, 'invited_by': request.user},
        )
        serializer.is_valid(raise_exception=True)
        membership = serializer.save()

        return Response({'membership': CircleMemberSerializer(membership).data}, status=status.HTTP_201_CREATED)


class CircleMemberRemoveView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, circle_id, user_id):
        circle = get_object_or_404(Circle, id=circle_id)
        membership_to_remove = CircleMembership.objects.filter(circle=circle, user_id=user_id).select_related('user').first()
        if not membership_to_remove:
            return Response({'detail': _('Membership not found')}, status=status.HTTP_404_NOT_FOUND)

        requester_membership = CircleMembership.objects.filter(circle=circle, user=request.user).first()
        removing_self = request.user.id == user_id

        if not removing_self:
            if not (request.user.is_superuser or (requester_membership and requester_membership.role == UserRole.CIRCLE_ADMIN)):
                raise PermissionDenied(_('Only circle admins can remove other members'))
        else:
            if not requester_membership and not request.user.is_superuser:
                raise PermissionDenied(_('Not a member of this circle'))

        membership_to_remove.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CircleActivityView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, circle_id):
        circle = get_object_or_404(Circle, id=circle_id)
        membership = CircleMembership.objects.filter(circle=circle, user=request.user).first()
        if not (request.user.is_superuser or (membership and membership.role == UserRole.CIRCLE_ADMIN)):
            raise PermissionDenied(_('Only circle admins can view activity'))

        events = []
        memberships = circle.memberships.select_related('user').order_by('-created_at')
        for member in memberships:
            events.append(
                {
                    'type': 'member_joined',
                    'created_at': member.created_at,
                    'user': UserSerializer(member.user).data,
                    'role': member.role,
                }
            )

        invitations = circle.invitations.order_by('-created_at')
        for invitation in invitations:
            events.append(
                {
                    'type': 'invitation',
                    'created_at': invitation.created_at,
                    'email': invitation.email,
                    'role': invitation.role,
                    'status': invitation.status,
                    'responded_at': invitation.responded_at,
                }
            )

        events.sort(key=lambda item: item['created_at'] or timezone.now(), reverse=True)

        return Response({'circle': CircleSerializer(circle).data, 'events': events})


class CircleInvitationRespondView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, invitation_id):
        invitation = get_object_or_404(CircleInvitation, id=invitation_id)
        if invitation.email.lower() != request.user.email.lower():
            raise PermissionDenied(_('Invitation does not belong to this user'))

        serializer = CircleInvitationResponseSerializer(data=request.data, context={'invitation': invitation})
        serializer.is_valid(raise_exception=True)
        action = serializer.validated_data['action']

        if invitation.status != CircleInvitationStatus.PENDING:
            return Response({'detail': _('Invitation is no longer pending')}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            if action == 'accept':
                membership, created = CircleMembership.objects.get_or_create(
                    user=request.user,
                    circle=invitation.circle,
                    defaults={'role': invitation.role, 'invited_by': invitation.invited_by},
                )
                if not created and membership.role != invitation.role:
                    membership.role = invitation.role
                    membership.save(update_fields=['role'])
                invitation.status = CircleInvitationStatus.ACCEPTED
                message = _('Invitation accepted')
            else:
                invitation.status = CircleInvitationStatus.DECLINED
                message = _('Invitation declined')
            invitation.responded_at = timezone.now()
            invitation.save(update_fields=['status', 'responded_at'])

        response = {'detail': message, 'circle': CircleSerializer(invitation.circle).data}
        return Response(response)


class CircleInvitationAcceptView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = CircleInvitationAcceptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = _pop_token('circle-invite', serializer.validated_data['token'])
        if not payload:
            return Response({'detail': _('Invalid or expired token')}, status=status.HTTP_400_BAD_REQUEST)

        invitation = CircleInvitation.objects.filter(
            id=payload['invitation_id'],
            status=CircleInvitationStatus.PENDING,
        ).select_related('circle', 'invited_by').first()
        if not invitation:
            return Response({'detail': _('Invitation not found')}, status=status.HTTP_404_NOT_FOUND)
        if invitation.email.lower() != payload.get('email', '').lower():
            return Response({'detail': _('Invitation mismatch')}, status=status.HTTP_400_BAD_REQUEST)

        existing_user = User.objects.filter(email__iexact=invitation.email).first()
        if existing_user:
            return Response({'detail': _('Email already registered. Please log in and ask an admin to reissue membership.')}, status=status.HTTP_409_CONFLICT)

        username = serializer.validated_data['username']
        password = serializer.validated_data['password']

        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                email=invitation.email,
                password=password,
                role=UserRole.CIRCLE_MEMBER,
            )
            user.email_verified = True
            user.save(update_fields=['email_verified'])

            CircleMembership.objects.create(
                user=user,
                circle=invitation.circle,
                role=invitation.role,
                invited_by=invitation.invited_by,
            )
            invitation.status = CircleInvitationStatus.ACCEPTED
            invitation.responded_at = timezone.now()
            invitation.save(update_fields=['status', 'responded_at'])

        response = {
            'detail': _('Invitation accepted'),
            'user': UserSerializer(user).data,
            'circle': CircleSerializer(invitation.circle).data,
            'tokens': _get_tokens_for_user(user),
        }
        return Response(response, status=status.HTTP_201_CREATED)


class ChildProfileUpgradeRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, child_id):
        child = get_object_or_404(ChildProfile, id=child_id)
        membership = CircleMembership.objects.filter(circle=child.circle, user=request.user).first()
        if not membership or membership.role != UserRole.CIRCLE_ADMIN:
            raise PermissionDenied(_('Only circle admins can upgrade child profiles'))

        serializer = ChildProfileUpgradeRequestSerializer(data=request.data, context={'child': child})
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            child.pending_invite_email = serializer.validated_data['email']
            child.upgrade_status = ChildProfileUpgradeStatus.PENDING
            child.save(update_fields=['pending_invite_email', 'upgrade_status', 'updated_at'])

            token = _store_token(
                'child-upgrade',
                {
                    'child_id': str(child.id),
                    'circle_id': child.circle_id,
                    'email': child.pending_invite_email,
                    'issued_at': timezone.now().isoformat(),
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

    def post(self, request):
        serializer = ChildProfileUpgradeConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = _pop_token('child-upgrade', serializer.validated_data['token'])
        if not payload:
            return Response({'detail': _('Invalid or expired token')}, status=status.HTTP_400_BAD_REQUEST)

        child = ChildProfile.objects.filter(id=payload['child_id']).select_related('circle').first()
        if not child:
            return Response({'detail': _('Child profile not found')}, status=status.HTTP_404_NOT_FOUND)
        if child.linked_user:
            return Response({'detail': _('Child profile already linked')}, status=status.HTTP_400_BAD_REQUEST)

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
            child.save(update_fields=['linked_user', 'upgrade_status', 'pending_invite_email', 'updated_at'])

        return Response(
            {
                'detail': _('Account created'),
                'user': UserSerializer(user).data,
                'tokens': _get_tokens_for_user(user),
            },
            status=status.HTTP_201_CREATED,
        )
