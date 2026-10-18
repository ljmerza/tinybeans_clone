"""The agent API, mounted at ``/api/agent/v1/`` (token management lives in ``mysite.users.urls``)."""

from django.urls import path

from .views import AgentMilestoneSuggestionView, AgentPostDetailView, AgentPostListView, AgentWhoAmIView

app_name = "agent_api"

urlpatterns = [
    path("whoami/", AgentWhoAmIView.as_view(), name="whoami"),
    path("posts/", AgentPostListView.as_view(), name="post-list"),
    path("posts/<uuid:post_id>/", AgentPostDetailView.as_view(), name="post-detail"),
    path("milestone-suggestions/", AgentMilestoneSuggestionView.as_view(), name="milestone-suggestion-create"),
]
