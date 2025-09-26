from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    OpenApiTypes,
    extend_schema,
)

from .models import (
    ChildGuardianConsent,
    ChildProfile,
    ChildProfileUpgradeStatus,
    ChildUpgradeEventType,
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
from .token_utils import (
    DEFAULT_TOKEN_TTL_SECONDS,
    delete_token,
    pop_token,
    store_token,
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

TOKEN_TTL_SECONDS = DEFAULT_TOKEN_TTL_SECONDS
REFRESH_COOKIE_NAME = 'refresh_token'
REFRESH_COOKIE_PATH = '/api/users/token/refresh/'


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    secure = not settings.DEBUG
    max_age = int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds())
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        path=REFRESH_COOKIE_PATH,
        max_age=max_age,
        httponly=True,
        secure=secure,
        samesite='Strict' if secure else 'Lax',
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)


def _get_tokens_for_user(user: User) -> dict:
    refresh = RefreshToken.for_user(user)
    return {'refresh': str(refresh), 'access': str(refresh.access_token)}


class SignupView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = SignupSerializer

    @extend_schema(
        description='Register a new account, optionally defer circle creation, and receive an access token (refresh token stored as an HTTP-only cookie).',
        request=SignupSerializer,
        responses={
            201: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description='Signup successful; returns created user, circle (if created), tokens, and verification token.',
            )
        },
    )
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, circle = serializer.save()

        verification_token = store_token(
            'verify-email',
            {'user_id': user.id, 'issued_at': timezone.now().isoformat()},
            ttl=TOKEN_TTL_SECONDS,
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

        tokens = _get_tokens_for_user(user)
        data = serializer.to_representation((user, circle))
        data['tokens'] = {'access': tokens['access']}
        data['verification_token'] = verification_token
        response = Response(data, status=status.HTTP_201_CREATED)
        _set_refresh_cookie(response, tokens['refresh'])
        return response


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer

    @extend_schema(
        description='Authenticate with username/password and receive an access token (refresh token stored in HTTP-only cookie).',
        request=LoginSerializer,
        responses={200: OpenApiResponse(response=OpenApiTypes.OBJECT, description='JWT tokens and user payload')},
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        tokens = _get_tokens_for_user(user)
        data = {
            'user': UserSerializer(user).data,
            'tokens': {'access': tokens['access']},
        }
        response = Response(data)
        _set_refresh_cookie(response, tokens['refresh'])
        return response


class EmailVerificationResendView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = EmailVerificationSerializer

    @extend_schema(
        description='Request that a new email verification message be sent to a user.',
        request=EmailVerificationSerializer,
        responses={202: OpenApiResponse(response=OpenApiTypes.OBJECT, description='Verification email scheduled')},
    )
    def post(self, request):
        serializer = EmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token = store_token(
            'verify-email',
            {'user_id': user.id, 'issued_at': timezone.now().isoformat()},
            ttl=TOKEN_TTL_SECONDS,
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


class TokenRefreshCookieView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        description='Obtain a new access token using the refresh token stored in the HTTP-only cookie.',
        request=None,
        responses={
            200: OpenApiResponse(response=OpenApiTypes.OBJECT, description='New access token issued.'),
            401: OpenApiResponse(description='Missing or invalid refresh token cookie.'),
        },
    )
    def post(self, request):
        refresh_token = request.COOKIES.get(REFRESH_COOKIE_NAME)
        if not refresh_token:
            return Response({'detail': _('Refresh token cookie missing.')}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = TokenRefreshSerializer(data={'refresh': refresh_token})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError:
            response = Response({'detail': _('Invalid or expired refresh token.')}, status=status.HTTP_401_UNAUTHORIZED)
            _clear_refresh_cookie(response)
            return response

        data = serializer.validated_data
        access_token = data['access']
        new_refresh = data.get('refresh', refresh_token)

        response = Response({'access': access_token})
        _set_refresh_cookie(response, new_refresh)
        return response


class EmailVerificationConfirmView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = EmailVerificationConfirmSerializer

    @extend_schema(
        description='Confirm email ownership using a verification token.',
        request=EmailVerificationConfirmSerializer,
        responses={200: OpenApiResponse(response=OpenApiTypes.OBJECT, description='Email successfully verified')},
    )
    def post(self, request):
        serializer = EmailVerificationConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = pop_token('verify-email', serializer.validated_data['token'])
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
    serializer_class = PasswordResetRequestSerializer

    @extend_schema(
        description='Initiate the password reset flow for a user by email or username.',
        request=PasswordResetRequestSerializer,
        responses={202: OpenApiResponse(response=OpenApiTypes.OBJECT, description='Password reset email scheduled')},
    )
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        if user:
            token = store_token(
                'password-reset',
                {'user_id': user.id, 'issued_at': timezone.now().isoformat()},
                ttl=TOKEN_TTL_SECONDS,
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
    serializer_class = PasswordResetConfirmSerializer

    @extend_schema(
        description='Complete a password reset using a valid reset token.',
        request=PasswordResetConfirmSerializer,
        responses={200: OpenApiResponse(response=OpenApiTypes.OBJECT, description='Password reset completed')},
    )
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = pop_token('password-reset', serializer.validated_data['token'])
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
    serializer_class = PasswordChangeSerializer

    @extend_schema(
        description='Allow an authenticated user to change their password and rotate tokens (refresh token stored in HTTP-only cookie).',
        request=PasswordChangeSerializer,
        responses={200: OpenApiResponse(response=OpenApiTypes.OBJECT, description='Password changed successfully with new tokens')},
    )
    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data['password'])
        user.save(update_fields=['password'])
        tokens = _get_tokens_for_user(user)
        response = Response({'detail': _('Password changed'), 'tokens': {'access': tokens['access']}})
        _set_refresh_cookie(response, tokens['refresh'])
        return response


class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserProfileSerializer

    @extend_schema(
        description='Retrieve profile metadata for the authenticated user.',
        responses={200: OpenApiResponse(response=OpenApiTypes.OBJECT, description='Authenticated user profile data')},
    )
    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response({'user': serializer.data})

    @extend_schema(
        description='Update selected profile fields (name, etc.) for the authenticated user.',
        request=UserProfileSerializer,
        responses={200: OpenApiResponse(response=OpenApiTypes.OBJECT)},
    )
    def patch(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'user': serializer.data})


class EmailPreferencesView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = EmailPreferencesSerializer

    def get_object(self, request):
        circle_id = request.query_params.get('circle_id')
        circle = None
        if circle_id:
            circle = get_object_or_404(Circle, id=circle_id)
            if not CircleMembership.objects.filter(circle=circle, user=request.user).exists():
                raise PermissionDenied(_('Not a member of this circle'))
        prefs, _ = UserNotificationPreferences.objects.get_or_create(user=request.user, circle=circle)
        return prefs

    @extend_schema(
        description='Fetch notification preferences, optionally scoped to a specific circle.',
        parameters=[
            OpenApiParameter(
                name='circle_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Optional circle context to fetch per-circle overrides.',
                required=False,
            )
        ],
        responses=EmailPreferencesSerializer,
    )
    def get(self, request):
        prefs = self.get_object(request)
        return Response(EmailPreferencesSerializer(prefs).data)

    @extend_schema(
        description='Update notification preferences globally or for a specific circle.',
        parameters=[
            OpenApiParameter(
                name='circle_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Optional circle context when updating per-circle overrides.',
                required=False,
            )
        ],
        request=EmailPreferencesSerializer,
        responses=EmailPreferencesSerializer,
    )
    def patch(self, request):
        prefs = self.get_object(request)
        serializer = EmailPreferencesSerializer(prefs, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class UserCircleListView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CircleMembershipSerializer

    @extend_schema(
        description='List all circles the authenticated user belongs to, including membership roles.',
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description='List of circle memberships for the authenticated user.',
            )
        }
    )
    def get(self, request):
        memberships = (
            CircleMembership.objects.filter(user=request.user)
            .select_related('circle')
            .order_by('circle__name')
        )
        serializer = CircleMembershipSerializer(memberships, many=True)
        return Response({'circles': serializer.data})

    @extend_schema(
        description='Create a new circle owned by the authenticated user.',
        request=CircleCreateSerializer,
        responses={
            201: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description='Circle created and returned with metadata.',
            )
        },
    )
    def post(self, request):
        serializer = CircleCreateSerializer(data=request.data, context={'user': request.user})
        serializer.is_valid(raise_exception=True)
        circle = serializer.save()
        return Response({'circle': CircleSerializer(circle).data}, status=status.HTTP_201_CREATED)


class CircleDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CircleCreateSerializer

    @extend_schema(
        description='Update circle metadata (name, slug) for an owned circle.',
        request=CircleCreateSerializer,
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description='Circle details updated successfully.',
            )
        },
    )
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
    serializer_class = CircleInvitationCreateSerializer

    @extend_schema(
        description='Invite a new member to join a circle via email.',
        request=CircleInvitationCreateSerializer,
        responses={
            202: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description='Invitation created and email queued.',
            )
        },
    )
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

        token = store_token(
            'circle-invite',
            {
                'invitation_id': str(invitation.id),
                'circle_id': circle.id,
                'email': invitation.email,
                'role': invitation.role,
                'issued_at': timezone.now().isoformat(),
            },
            ttl=TOKEN_TTL_SECONDS,
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
    serializer_class = CircleInvitationSerializer

    @extend_schema(
        description='Return pending circle invitations for the authenticated user.',
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description='Pending invitations for the authenticated user.',
            )
        }
    )
    def get(self, request):
        invitations = CircleInvitation.objects.filter(
            email__iexact=request.user.email,
            status=CircleInvitationStatus.PENDING,
        ).select_related('circle')
        data = CircleInvitationSerializer(invitations, many=True).data
        return Response({'invitations': data})


class CircleMemberListView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CircleMemberSerializer

    @extend_schema(
        description='List members of a circle including their roles.',
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description='Members of the requested circle with roles.',
            )
        }
    )
    def get(self, request, circle_id):
        circle = get_object_or_404(Circle, id=circle_id)
        membership = CircleMembership.objects.filter(circle=circle, user=request.user).first()
        if not (request.user.is_superuser or (membership and membership.role == UserRole.CIRCLE_ADMIN)):
            raise PermissionDenied(_('Only circle admins can view members'))

        memberships = CircleMembership.objects.filter(circle=circle).select_related('user').order_by('user__username')
        serializer = CircleMemberSerializer(memberships, many=True)
        return Response({'circle': CircleSerializer(circle).data, 'members': serializer.data})

    @extend_schema(
        description='Add an existing user to a circle with an optional role override.',
        request=CircleMemberAddSerializer,
        responses={
            201: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description='Membership created for user in circle.',
            )
        },
    )
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
    serializer_class = CircleMemberSerializer

    @extend_schema(
        description='Remove a member (or yourself) from a circle.',
        responses={204: OpenApiResponse(description='Membership removed.')},
    )
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
    serializer_class = CircleSerializer

    @extend_schema(
        description='View recent membership and invitation events for a circle.',
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description='Aggregation of circle membership and invitation events.',
            )
        }
    )
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
    serializer_class = CircleInvitationResponseSerializer

    @extend_schema(
        description='Accept or decline a pending invitation that belongs to the authenticated user.',
        request=CircleInvitationResponseSerializer,
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description='Invitation response processed for authenticated user.',
            )
        },
    )
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
    serializer_class = CircleInvitationAcceptSerializer

    @extend_schema(
        description='Complete an invitation-based signup flow using a one-time token.',
        request=CircleInvitationAcceptSerializer,
        responses={
            201: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description='Invitation accepted and new member onboarded.',
            )
        },
    )
    def post(self, request):
        serializer = CircleInvitationAcceptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = pop_token('circle-invite', serializer.validated_data['token'])
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
