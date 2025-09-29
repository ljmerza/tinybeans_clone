"""Circle management and invitation views."""
from __future__ import annotations

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
    Circle,
    CircleInvitation,
    CircleInvitationStatus,
    CircleMembership,
    User,
    UserRole,
)
from ..serializers import (
    CircleCreateSerializer,
    CircleInvitationAcceptSerializer,
    CircleInvitationCreateSerializer,
    CircleInvitationResponseSerializer,
    CircleInvitationSerializer,
    CircleMemberAddSerializer,
    CircleMemberSerializer,
    CircleMembershipSerializer,
    CircleSerializer,
    UserSerializer,
)
from ..tasks import CIRCLE_INVITATION_TEMPLATE, send_email_task
from ..token_utils import (
    TOKEN_TTL_SECONDS,
    get_tokens_for_user,
    pop_token,
    store_token,
)


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
        description='Create a new circle owned by the authenticated user. Email verification is required.',
        request=CircleCreateSerializer,
        responses={
            201: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description='Circle created and returned with metadata.',
            ),
            400: OpenApiResponse(
                description='Email verification required or validation error.',
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
            'tokens': get_tokens_for_user(user),
        }
        return Response(response, status=status.HTTP_201_CREATED)
