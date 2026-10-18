"""API tokens work on the four agent endpoints and nowhere else."""

import pytest
from django.conf import settings
from django.urls import URLPattern, URLResolver, get_resolver, reverse
from rest_framework import status

from mysite.agent_api.authentication import CircleApiTokenAuthentication
from mysite.agent_api.views import (
    AgentMilestoneSuggestionView,
    AgentPostDetailView,
    AgentPostListView,
    AgentWhoAmIView,
)
from mysite.albums.models import Album
from mysite.albums.tests.helpers import make_keep

AGENT_VIEWS = {AgentWhoAmIView, AgentPostListView, AgentPostDetailView, AgentMilestoneSuggestionView}


def _view_classes(patterns):
    for pattern in patterns:
        if isinstance(pattern, URLResolver):
            yield from _view_classes(pattern.url_patterns)
        elif isinstance(pattern, URLPattern):
            view_class = getattr(pattern.callback, "cls", None) or getattr(pattern.callback, "view_class", None)
            if view_class is not None:
                yield view_class


def test_only_agent_views_accept_api_tokens():
    views = set(_view_classes(get_resolver().url_patterns))
    token_views = {
        view
        for view in views
        if any(
            isinstance(auth, type) and issubclass(auth, CircleApiTokenAuthentication)
            for auth in getattr(view, "authentication_classes", ())
        )
    }

    assert len(views) > 50  # the walk found the whole API
    assert token_views == AGENT_VIEWS
    assert all(view.__module__ == "mysite.agent_api.views.agent" for view in token_views)


def test_agent_views_accept_nothing_but_api_tokens():
    for view in AGENT_VIEWS:
        assert view.authentication_classes == [CircleApiTokenAuthentication]


def test_default_authentication_is_jwt_only():
    assert settings.REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] == (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    )


@pytest.mark.django_db
class TestTokenElsewhere:
    @pytest.fixture
    def album_and_keep(self, circle, admin):
        return Album.objects.create(circle=circle, name="Beach", created_by=admin), make_keep(circle, admin)

    def test_feed(self, agent):
        assert agent.get(reverse("keeps:keep-feed")).status_code == status.HTTP_401_UNAUTHORIZED

    def test_albums(self, agent):
        assert agent.get(reverse("albums:album-list-create")).status_code == status.HTTP_401_UNAUTHORIZED

    def test_album_write(self, agent, album_and_keep):
        album, keep = album_and_keep
        response = agent.post(reverse("albums:album-keep", args=[album.id, keep.id]))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert not album.album_keeps.exists()

    def test_profile(self, agent):
        assert agent.get(reverse("user-profile")).status_code == status.HTTP_401_UNAUTHORIZED

    def test_token_management(self, agent, circle):
        response = agent.get(reverse("circle-api-token-list", args=[circle.id]))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
