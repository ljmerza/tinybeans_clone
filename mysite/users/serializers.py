from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

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


class CircleSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Circle
        fields = ['id', 'name', 'slug', 'member_count']

    def get_member_count(self, obj):
        return obj.memberships.count()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'email_verified', 'date_joined']


class CircleMembershipSerializer(serializers.ModelSerializer):
    circle = CircleSerializer()

    class Meta:
        model = CircleMembership
        fields = ['id', 'circle', 'role', 'created_at']


class CircleMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = CircleMembership
        fields = ['id', 'user', 'role', 'created_at']


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'email_verified', 'date_joined']
        read_only_fields = ['id', 'role', 'email_verified', 'date_joined']


class CircleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Circle
        fields = ['id', 'name', 'slug', 'created_at']
        read_only_fields = ['id', 'slug', 'created_at']

    def create(self, validated_data):
        user = self.context['user']
        circle = Circle.objects.create(created_by=user, **validated_data)
        CircleMembership.objects.create(user=user, circle=circle, role=UserRole.CIRCLE_ADMIN)
        return circle


class CircleMemberAddSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    role = serializers.ChoiceField(choices=UserRole.choices, required=False)

    def validate(self, attrs):
        circle = self.context['circle']
        try:
            user = User.objects.get(id=attrs['user_id'])
        except User.DoesNotExist:
            raise serializers.ValidationError({'user_id': _('User not found')})

        if CircleMembership.objects.filter(circle=circle, user=user).exists():
            raise serializers.ValidationError({'user_id': _('User already belongs to this circle')})

        attrs['user'] = user
        attrs['role'] = attrs.get('role') or UserRole.CIRCLE_MEMBER
        return attrs

    def create(self, validated_data):
        circle = self.context['circle']
        invited_by = self.context.get('invited_by')
        membership = CircleMembership.objects.create(
            circle=circle,
            user=validated_data['user'],
            role=validated_data['role'],
            invited_by=invited_by,
        )
        return membership

class SignupSerializer(serializers.ModelSerializer):
    circle_name = serializers.CharField(required=False, allow_blank=True)
    role = serializers.ChoiceField(choices=UserRole.choices, required=False)
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'circle_name', 'role']

    def validate_role(self, value):
        if value == UserRole.CIRCLE_ADMIN:
            return value
        return value or UserRole.CIRCLE_MEMBER

    def create(self, validated_data):
        circle_name = validated_data.pop('circle_name', '').strip()
        role = validated_data.pop('role', UserRole.CIRCLE_MEMBER)
        password = validated_data.pop('password')

        user = User.objects.create_user(password=password, role=role, **validated_data)

        if not circle_name:
            circle_name = f"{user.username}'s Circle"

        circle = Circle.objects.create(name=circle_name, created_by=user)
        CircleMembership.objects.create(user=user, circle=circle, role=UserRole.CIRCLE_ADMIN)
        user.role = UserRole.CIRCLE_ADMIN
        user.save(update_fields=['role'])

        return user, circle

    def to_representation(self, instance_tuple):
        user, circle = instance_tuple
        data = UserSerializer(user).data
        data['circle'] = CircleSerializer(circle).data
        return data


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(username=attrs['username'], password=attrs['password'])
        if not user:
            raise serializers.ValidationError(_('Invalid username or password'))
        if not user.is_active:
            raise serializers.ValidationError(_('User account is inactive'))
        attrs['user'] = user
        return attrs


class EmailVerificationSerializer(serializers.Serializer):
    identifier = serializers.CharField()

    def validate(self, attrs):
        identifier = attrs['identifier']
        try:
            user = User.objects.get(username=identifier)
        except User.DoesNotExist:
            user = User.objects.filter(email__iexact=identifier).first()
        if not user:
            raise serializers.ValidationError(_('User not found'))
        attrs['user'] = user
        return attrs


class EmailVerificationConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()


class PasswordResetRequestSerializer(serializers.Serializer):
    identifier = serializers.CharField()

    def validate(self, attrs):
        identifier = attrs['identifier']
        user = User.objects.filter(username=identifier).first()
        if not user:
            user = User.objects.filter(email__iexact=identifier).first()
        attrs['user'] = user
        return attrs


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': _('Passwords do not match')})
        return attrs


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        user = self.context['request'].user
        if not user.check_password(attrs['current_password']):
            raise serializers.ValidationError({'current_password': _('Current password is incorrect')})
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': _('Passwords do not match')})
        return attrs


class EmailPreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserNotificationPreferences
        fields = ['notify_new_media', 'notify_weekly_digest', 'channel']


class CircleInvitationSerializer(serializers.ModelSerializer):
    circle = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = CircleInvitation
        fields = ['id', 'circle', 'email', 'role', 'status', 'created_at', 'responded_at']
        read_only_fields = ['id', 'circle', 'status', 'created_at', 'responded_at']


class CircleInvitationCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=UserRole.choices, required=False)

    def validate(self, attrs):
        circle = self.context['circle']
        email = attrs['email'].lower()
        if CircleMembership.objects.filter(circle=circle, user__email__iexact=email).exists():
            raise serializers.ValidationError({'email': _('User already belongs to this circle')})
        if CircleInvitation.objects.filter(
            circle=circle,
            email__iexact=email,
            status=CircleInvitationStatus.PENDING,
        ).exists():
            raise serializers.ValidationError({'email': _('An invitation is already pending for this email')})
        attrs['email'] = email
        attrs['role'] = attrs.get('role') or UserRole.CIRCLE_MEMBER
        return attrs


class CircleInvitationResponseSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['accept', 'decline'])

    def validate(self, attrs):
        invitation = self.context['invitation']
        if invitation.status != CircleInvitationStatus.PENDING:
            raise serializers.ValidationError(_('Invitation is no longer pending'))
        attrs['action'] = attrs['action'].lower()
        return attrs


class CircleInvitationAcceptSerializer(serializers.Serializer):
    token = serializers.CharField()
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': _('Passwords do not match')})
        if User.objects.filter(username=attrs['username']).exists():
            raise serializers.ValidationError({'username': _('Username is already taken')})
        return attrs


class ChildProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChildProfile
        fields = ['id', 'display_name', 'birthdate', 'avatar_url', 'upgrade_status', 'pending_invite_email', 'linked_user']
        read_only_fields = ['upgrade_status', 'pending_invite_email', 'linked_user']


class ChildProfileUpgradeRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    username = serializers.CharField(required=False)

    def validate(self, attrs):
        child = self.context['child']
        if child.upgrade_status == ChildProfileUpgradeStatus.LINKED:
            raise serializers.ValidationError(_('Child profile already linked'))
        attrs['email'] = attrs['email'].lower()
        if User.objects.filter(email__iexact=attrs['email']).exists():
            raise serializers.ValidationError({'email': _('A user with this email already exists. Ask them to log in.')})
        username = attrs.get('username')
        if username and User.objects.filter(username=username).exists():
            raise serializers.ValidationError({'username': _('Username is already taken')})
        return attrs


class ChildProfileUpgradeConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': _('Passwords do not match')})
        if User.objects.filter(username=attrs['username']).exists():
            raise serializers.ValidationError({'username': _('Username is already taken')})
        return attrs
