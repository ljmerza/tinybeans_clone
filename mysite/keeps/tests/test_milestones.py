"""Milestones: feed output, creating and changing them, the milestones list, and the children list."""

from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework import status
from rest_framework.test import APIClient

from mysite.circles.models import Circle, CircleMembership
from mysite.keeps.models import Keep, KeepMedia, KeepType, Milestone, MilestoneType
from mysite.keeps.serializers.milestones import age_on
from mysite.users.models import UserRole
from mysite.users.models.child_profile import ChildProfile

User = get_user_model()

KEEPS_URL = "/api/keeps/"
FEED_URL = "/api/keeps/feed/"
MILESTONES_URL = "/api/keeps/feed/milestones/"
CHILDREN_URL = "/api/keeps/children/"
BASE_TIME = datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc)


def milestone_url(keep_id):
    return f"/api/keeps/{keep_id}/milestone/"


class FakeStorageBackend:
    def get_url(self, storage_key, expires_in=3600):
        return f"https://cdn.test/{storage_key}"


@pytest.fixture(autouse=True)
def fake_storage():
    with patch("mysite.keeps.storage.get_storage_backend", return_value=FakeStorageBackend()):
        yield


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user():
    return User.objects.create_user(email="milestones@example.com", password="testpass123")


@pytest.fixture
def circle(user):
    """The creator is the circle's admin (membership created by signal)."""
    return Circle.objects.create(name="Milestone Family", created_by=user)


@pytest.fixture
def member(circle):
    """A plain member of the same circle."""
    other = User.objects.create_user(email="milestones-member@example.com", password="memberpass123")
    CircleMembership.objects.create(user=other, circle=circle, role=UserRole.CIRCLE_MEMBER)
    return other


@pytest.fixture
def outsider():
    return User.objects.create_user(email="milestones-outsider@example.com", password="outsiderpass123")


@pytest.fixture
def other_circle(outsider):
    return Circle.objects.create(name="Other Family", created_by=outsider)


@pytest.fixture
def emma(circle):
    return ChildProfile.objects.create(circle=circle, display_name="Emma", birthdate=date(2025, 5, 1))


@pytest.fixture
def liam(circle):
    return ChildProfile.objects.create(circle=circle, display_name="Liam")


@pytest.fixture
def stranger_child(other_circle):
    return ChildProfile.objects.create(circle=other_circle, display_name="Stranger")


def make_keep(circle, user, when=BASE_TIME, *, title="Memory", media=True):
    keep = Keep.objects.create(
        circle=circle,
        created_by=user,
        keep_type=KeepType.MEDIA if media else KeepType.NOTE,
        title=title,
        date_of_memory=when,
    )
    if media:
        KeepMedia.objects.create(
            keep=keep,
            media_type="photo",
            storage_key_original=f"original/{keep.id}",
            storage_key_gallery=f"gallery/{keep.id}",
            original_filename="file.jpg",
            content_type="image/jpeg",
            thumbnails_generated=True,
        )
    return keep


def make_milestone(keep, milestone_type=MilestoneType.FIRST_STEPS, child=None):
    keep.keep_type = KeepType.MILESTONE
    keep.save(update_fields=["keep_type"])
    return Milestone.objects.create(keep=keep, milestone_type=milestone_type, child_profile=child)


def titles(response):
    return [item["title"] for item in response.data["results"]]


class TestAgeOn:
    @pytest.mark.parametrize(
        ("birthdate", "day", "expected"),
        [
            (date(2025, 5, 1), date(2025, 5, 1), {"years": 0, "months": 0, "days": 0}),
            (date(2025, 5, 1), date(2025, 5, 20), {"years": 0, "months": 0, "days": 19}),
            (date(2025, 5, 1), date(2026, 7, 1), {"years": 1, "months": 2, "days": 0}),
            (date(2025, 5, 15), date(2026, 7, 1), {"years": 1, "months": 1, "days": 16}),
            (date(2024, 7, 1), date(2026, 7, 1), {"years": 2, "months": 0, "days": 0}),
            # A birthday on the 31st falls on the last day of shorter months.
            (date(2025, 1, 31), date(2025, 2, 28), {"years": 0, "months": 1, "days": 0}),
            (date(2025, 1, 31), date(2025, 3, 1), {"years": 0, "months": 1, "days": 1}),
        ],
    )
    def test_whole_years_months_and_days(self, birthdate, day, expected):
        assert age_on(birthdate, day) == expected

    def test_unknown_or_before_birth(self):
        assert age_on(None, date(2026, 1, 1)) is None
        assert age_on(date(2026, 1, 2), date(2026, 1, 1)) is None


@pytest.mark.django_db
class TestFeedMilestone:
    def test_regular_posts_have_no_milestone(self, api_client, user, circle):
        keep = make_keep(circle, user)
        api_client.force_authenticate(user=user)

        response = api_client.get(f"{FEED_URL}{keep.id}/")

        assert response.data["milestone"] is None

    def test_milestone_with_child_and_age_on_the_memory_date(self, api_client, user, circle, emma):
        keep = make_keep(circle, user, datetime(2026, 7, 1, 23, 30, tzinfo=timezone.utc))
        make_milestone(keep, MilestoneType.FIRST_STEPS, emma)
        api_client.force_authenticate(user=user)

        response = api_client.get(f"{FEED_URL}{keep.id}/")

        assert response.data["milestone"] == {
            "milestone_type": "first_steps",
            "child": {"id": str(emma.id), "display_name": "Emma"},
            "child_age": {"years": 1, "months": 2, "days": 0},
            "age_at_milestone": "",
        }

    def test_child_without_birthdate_has_no_age(self, api_client, user, circle, liam):
        keep = make_keep(circle, user)
        make_milestone(keep, MilestoneType.FIRST_WORD, liam)
        api_client.force_authenticate(user=user)

        milestone = api_client.get(FEED_URL).data["results"][0]["milestone"]

        assert milestone["child"] == {"id": str(liam.id), "display_name": "Liam"}
        assert milestone["child_age"] is None

    def test_milestone_without_child(self, api_client, user, circle):
        keep = make_keep(circle, user)
        Milestone.objects.create(keep=keep, milestone_type=MilestoneType.OTHER, age_at_milestone="18 months")
        api_client.force_authenticate(user=user)

        milestone = api_client.get(FEED_URL).data["results"][0]["milestone"]

        assert milestone == {
            "milestone_type": "other",
            "child": None,
            "child_age": None,
            "age_at_milestone": "18 months",
        }

    def test_query_count_does_not_grow_with_milestones(self, api_client, user, circle, emma):
        def add_keeps(count, offset):
            for n in range(count):
                keep = make_keep(circle, user, BASE_TIME - timedelta(days=offset + n))
                make_milestone(keep, child=emma)

        api_client.force_authenticate(user=user)
        add_keeps(2, 0)
        with CaptureQueriesContext(connection) as small:
            api_client.get(FEED_URL)
        add_keeps(8, 2)
        with CaptureQueriesContext(connection) as large:
            api_client.get(FEED_URL)

        assert len(large) == len(small)

    def test_detail_serializer_names_the_child(self, api_client, user, circle, emma):
        keep = make_keep(circle, user)
        make_milestone(keep, child=emma)
        api_client.force_authenticate(user=user)

        response = api_client.get(f"{KEEPS_URL}{keep.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["milestone"]["child_name"] == "Emma"


@pytest.mark.django_db
class TestCreateMilestoneKeep:
    def post(self, api_client, circle, milestone_data, keep_type="milestone"):
        return api_client.post(
            KEEPS_URL,
            {"circle": circle.id, "keep_type": keep_type, "title": "Steps!", "milestone_data": milestone_data},
            format="json",
        )

    def test_creates_the_milestone_for_a_child_in_the_circle(self, api_client, user, circle, emma):
        api_client.force_authenticate(user=user)

        response = self.post(api_client, circle, {"milestone_type": "first_steps", "child_profile": str(emma.id)})

        assert response.status_code == status.HTTP_201_CREATED
        keep = Keep.objects.get(id=response.data["id"])
        assert keep.keep_type == KeepType.MILESTONE
        assert keep.milestone.milestone_type == MilestoneType.FIRST_STEPS
        assert keep.milestone.child_profile == emma

    def test_child_is_optional(self, api_client, user, circle):
        api_client.force_authenticate(user=user)

        response = self.post(api_client, circle, {"milestone_type": "birthday"})

        assert response.status_code == status.HTTP_201_CREATED
        assert Keep.objects.get(id=response.data["id"]).milestone.child_profile is None

    def test_rejects_a_child_from_another_circle(self, api_client, user, circle, stranger_child):
        api_client.force_authenticate(user=user)

        response = self.post(
            api_client, circle, {"milestone_type": "first_steps", "child_profile": str(stranger_child.id)}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "errors.milestone_child_not_in_circle" in str(response.data)
        assert Keep.objects.count() == 0
        assert Milestone.objects.count() == 0

    def test_rejects_an_unknown_type(self, api_client, user, circle):
        api_client.force_authenticate(user=user)

        response = self.post(api_client, circle, {"milestone_type": "first_moonwalk"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_milestone_data_still_needs_the_milestone_type(self, api_client, user, circle):
        api_client.force_authenticate(user=user)

        response = self.post(api_client, circle, {"milestone_type": "first_steps"}, keep_type="media")

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestSetMilestone:
    def test_requires_authentication(self, api_client, user, circle):
        keep = make_keep(circle, user)
        assert api_client.put(milestone_url(keep.id), {}, format="json").status_code == status.HTTP_401_UNAUTHORIZED
        assert api_client.delete(milestone_url(keep.id)).status_code == status.HTTP_401_UNAUTHORIZED

    def test_creator_marks_and_changes_a_milestone(self, api_client, member, circle, emma):
        keep = make_keep(circle, member)
        api_client.force_authenticate(user=member)

        response = api_client.put(
            milestone_url(keep.id), {"milestone_type": "first_tooth", "child_profile": str(emma.id)}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["milestone_type"] == "first_tooth"
        assert response.data["child"] == {"id": str(emma.id), "display_name": "Emma"}
        assert response.data["child_age"] == {"years": 1, "months": 2, "days": 0}
        keep.refresh_from_db()
        assert keep.keep_type == KeepType.MILESTONE

        # A second PUT replaces it; leaving the child out clears it.
        response = api_client.put(milestone_url(keep.id), {"milestone_type": "first_word"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert Milestone.objects.filter(keep=keep).count() == 1
        milestone = Milestone.objects.get(keep=keep)
        assert milestone.milestone_type == MilestoneType.FIRST_WORD
        assert milestone.child_profile is None

    def test_circle_admin_may_change_anyones_post(self, api_client, user, member, circle):
        keep = make_keep(circle, member)
        api_client.force_authenticate(user=user)

        response = api_client.put(milestone_url(keep.id), {"milestone_type": "birthday"}, format="json")

        assert response.status_code == status.HTTP_200_OK

    def test_other_members_may_not(self, api_client, user, member, circle):
        keep = make_keep(circle, user)
        api_client.force_authenticate(user=member)

        assert (
            api_client.put(milestone_url(keep.id), {"milestone_type": "birthday"}, format="json").status_code
            == status.HTTP_403_FORBIDDEN
        )
        assert api_client.delete(milestone_url(keep.id)).status_code == status.HTTP_403_FORBIDDEN
        assert not Milestone.objects.exists()

    def test_outsiders_get_404(self, api_client, user, circle, outsider):
        keep = make_keep(circle, user)
        api_client.force_authenticate(user=outsider)

        assert (
            api_client.put(milestone_url(keep.id), {"milestone_type": "birthday"}, format="json").status_code
            == status.HTTP_404_NOT_FOUND
        )
        assert api_client.delete(milestone_url(keep.id)).status_code == status.HTTP_404_NOT_FOUND

    def test_rejects_a_child_from_another_circle_or_a_missing_type(self, api_client, user, circle, stranger_child):
        keep = make_keep(circle, user)
        api_client.force_authenticate(user=user)

        foreign = api_client.put(
            milestone_url(keep.id),
            {"milestone_type": "birthday", "child_profile": str(stranger_child.id)},
            format="json",
        )
        missing = api_client.put(milestone_url(keep.id), {}, format="json")

        assert foreign.status_code == status.HTTP_400_BAD_REQUEST
        assert foreign.data["messages"][0]["i18n_key"] == "errors.milestone_child_not_in_circle"
        assert missing.status_code == status.HTTP_400_BAD_REQUEST
        assert not Milestone.objects.exists()

    @pytest.mark.parametrize(("media", "keep_type"), [(True, KeepType.MEDIA), (False, KeepType.NOTE)])
    def test_clearing_restores_the_post_type(self, api_client, user, circle, media, keep_type):
        keep = make_keep(circle, user, media=media)
        make_milestone(keep)
        api_client.force_authenticate(user=user)

        response = api_client.delete(milestone_url(keep.id))

        assert response.status_code == status.HTTP_204_NO_CONTENT
        keep.refresh_from_db()
        assert keep.keep_type == keep_type
        assert not Milestone.objects.exists()
        # Clearing again is a no-op.
        assert api_client.delete(milestone_url(keep.id)).status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.django_db
class TestMilestoneList:
    def test_requires_authentication(self, api_client):
        assert api_client.get(MILESTONES_URL).status_code == status.HTTP_401_UNAUTHORIZED

    def test_only_milestones_oldest_first(self, api_client, user, circle, emma):
        later = make_keep(circle, user, BASE_TIME, title="Steps")
        make_milestone(later, child=emma)
        earlier = make_keep(circle, user, BASE_TIME - timedelta(days=90), title="Tooth")
        make_milestone(earlier, MilestoneType.FIRST_TOOTH, emma)
        make_keep(circle, user, BASE_TIME - timedelta(days=30), title="Just a photo")
        api_client.force_authenticate(user=user)

        response = api_client.get(MILESTONES_URL)

        assert response.status_code == status.HTTP_200_OK
        assert titles(response) == ["Tooth", "Steps"]
        assert response.data["results"][0]["milestone"]["milestone_type"] == "first_tooth"

    def test_filters_to_one_child(self, api_client, user, circle, emma, liam):
        make_milestone(make_keep(circle, user, title="Emma's"), child=emma)
        make_milestone(make_keep(circle, user, title="Liam's"), child=liam)
        make_milestone(make_keep(circle, user, title="Nobody's"))
        api_client.force_authenticate(user=user)

        assert titles(api_client.get(MILESTONES_URL, {"child": str(liam.id)})) == ["Liam's"]

    def test_follows_feed_visibility(self, api_client, user, circle, outsider, other_circle, stranger_child):
        make_milestone(make_keep(other_circle, outsider, title="Not yours"), child=stranger_child)
        processing = make_keep(circle, user, title="Processing", media=False)
        processing.keep_type = KeepType.MEDIA
        processing.save(update_fields=["keep_type"])
        make_milestone(processing)  # no displayable media yet
        make_milestone(make_keep(circle, user, title="Mine"))
        api_client.force_authenticate(user=user)

        assert titles(api_client.get(MILESTONES_URL)) == ["Mine"]
        # Naming another circle's child shows nothing.
        assert titles(api_client.get(MILESTONES_URL, {"child": str(stranger_child.id)})) == []

    def test_filters_to_one_circle(self, api_client, user, circle):
        second = Circle.objects.create(name="Second Family", created_by=user)
        make_milestone(make_keep(circle, user, title="First circle"))
        make_milestone(make_keep(second, user, title="Second circle"))
        api_client.force_authenticate(user=user)

        assert titles(api_client.get(MILESTONES_URL, {"circle_slug": second.slug})) == ["Second circle"]

    def test_cursor_pagination_walks_every_milestone_once(self, api_client, user, circle):
        for n in range(5):
            make_milestone(make_keep(circle, user, BASE_TIME + timedelta(days=n), title=f"M{n}"))
        api_client.force_authenticate(user=user)

        seen = []
        response = api_client.get(MILESTONES_URL, {"page_size": 2})
        seen += titles(response)
        while response.data["next"]:
            response = api_client.get(response.data["next"])
            seen += titles(response)

        assert seen == ["M0", "M1", "M2", "M3", "M4"]

    def test_invalid_child_is_rejected(self, api_client, user):
        api_client.force_authenticate(user=user)

        assert api_client.get(MILESTONES_URL, {"child": "nope"}).status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestChildrenList:
    def test_requires_authentication(self, api_client):
        assert api_client.get(CHILDREN_URL).status_code == status.HTTP_401_UNAUTHORIZED

    def test_children_in_the_users_circles_with_milestone_counts(
        self, api_client, user, circle, emma, liam, stranger_child
    ):
        make_milestone(make_keep(circle, user), child=emma)
        make_milestone(make_keep(circle, user), MilestoneType.FIRST_WORD, emma)
        api_client.force_authenticate(user=user)

        response = api_client.get(CHILDREN_URL)

        assert response.status_code == status.HTTP_200_OK
        circle_info = {"id": circle.id, "name": circle.name, "slug": circle.slug}
        assert response.data == [
            {"id": str(emma.id), "display_name": "Emma", "circle": circle_info, "milestone_count": 2},
            {"id": str(liam.id), "display_name": "Liam", "circle": circle_info, "milestone_count": 0},
        ]
