from django.urls import path

from .views import (
    ChildProfileUpgradeConfirmView,
    ChildProfileUpgradeRequestView,
    CircleInvitationAcceptView,
    CircleInvitationCreateView,
    CircleInvitationListView,
    CircleInvitationRespondView,
    CircleActivityView,
    CircleDetailView,
    CircleMemberListView,
    CircleMemberRemoveView,
    CirclePetListView,
    CircleOnboardingStatusView,
    CircleOnboardingSkipView,
    EmailPreferencesView,
    PetProfileDetailView,
    UserProfileView,
    UserCircleListView,
)

urlpatterns = [
    path('me/', UserProfileView.as_view(), name='user-profile'),
    path('me/email-preferences/', EmailPreferencesView.as_view(), name='user-email-preferences'),

    path('circle-onboarding/', CircleOnboardingStatusView.as_view(), name='circle-onboarding-status'),
    path('circle-onboarding/skip/', CircleOnboardingSkipView.as_view(), name='circle-onboarding-skip'),
    
    path('circles/', UserCircleListView.as_view(), name='user-circle-list'),
    path('circles/<int:circle_id>/', CircleDetailView.as_view(), name='circle-detail'),
    path('circles/<int:circle_id>/invitations/', CircleInvitationCreateView.as_view(), name='circle-invitation-create'),
    path('circles/<int:circle_id>/members/', CircleMemberListView.as_view(), name='circle-member-list'),
    path('circles/<int:circle_id>/members/<int:user_id>/', CircleMemberRemoveView.as_view(), name='circle-member-remove'),
    path('circles/<int:circle_id>/activity/', CircleActivityView.as_view(), name='circle-activity'),
    path('circles/<int:circle_id>/pets/', CirclePetListView.as_view(), name='circle-pet-list'),
    
    path('invitations/accept/', CircleInvitationAcceptView.as_view(), name='circle-invitation-accept'),
    path('invitations/pending/', CircleInvitationListView.as_view(), name='circle-invitation-list'),
    path('invitations/<uuid:invitation_id>/respond/', CircleInvitationRespondView.as_view(), name='circle-invitation-respond'),
    
    path('child-profiles/<uuid:child_id>/upgrade/request/', ChildProfileUpgradeRequestView.as_view(), name='child-upgrade-request'),
    path('child-profiles/upgrade/confirm/', ChildProfileUpgradeConfirmView.as_view(), name='child-upgrade-confirm'),
    
    path('pets/<uuid:pet_id>/', PetProfileDetailView.as_view(), name='pet-detail'),
]

