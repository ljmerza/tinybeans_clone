from django.urls import path

from .views import (
    ChildProfileUpgradeConfirmView,
    ChildProfileUpgradeRequestView,
    CircleInvitationAcceptView,
    CircleInvitationCreateView,
    CircleInvitationListView,
    CircleInvitationRespondView,
    EmailPreferencesView,
    EmailVerificationConfirmView,
    EmailVerificationResendView,
    LoginView,
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    SignupView,
)

urlpatterns = [
    path('signup/', SignupView.as_view(), name='user-signup'),
    path('login/', LoginView.as_view(), name='user-login'),
    path('verify-email/resend/', EmailVerificationResendView.as_view(), name='user-verify-resend'),
    path('verify-email/confirm/', EmailVerificationConfirmView.as_view(), name='user-verify-confirm'),
    path('password-reset/request/', PasswordResetRequestView.as_view(), name='user-password-reset-request'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='user-password-reset-confirm'),
    path('password/change/', PasswordChangeView.as_view(), name='user-password-change'),
    path('email-preferences/', EmailPreferencesView.as_view(), name='user-email-preferences'),
    path('circles/<int:circle_id>/invitations/', CircleInvitationCreateView.as_view(), name='circle-invitation-create'),
    path('invitations/accept/', CircleInvitationAcceptView.as_view(), name='circle-invitation-accept'),
    path('invitations/pending/', CircleInvitationListView.as_view(), name='circle-invitation-list'),
    path('invitations/<uuid:invitation_id>/respond/', CircleInvitationRespondView.as_view(), name='circle-invitation-respond'),
    path('child-profiles/<uuid:child_id>/upgrade/request/', ChildProfileUpgradeRequestView.as_view(), name='child-upgrade-request'),
    path('child-profiles/upgrade/confirm/', ChildProfileUpgradeConfirmView.as_view(), name='child-upgrade-confirm'),
]
