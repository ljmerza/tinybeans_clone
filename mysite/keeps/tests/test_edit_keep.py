"""Editing a post (PATCH /api/keeps/<id>/): its title, caption, date and people, by its poster or a circle admin."""

from datetime import datetime, timezone

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from mysite.circles.models import Circle, CircleMembership
from mysite.keeps.models import Keep, KeepPerson, KeepType, Person
from mysite.users.models import ChildProfile, UserRole

User = get_user_model()

BASE_TIME = datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc)


def keep_url(keep_id):
    return f"/api/keeps/{keep_id}/"


def tagged(keep):
    return set(KeepPerson.objects.filter(keep=keep).values_list("person__name", flat=True))


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin():
    """The circle's creator, so its admin."""
    return User.objects.create_user(email="edit-admin@example.com", password="adminpass123")


@pytest.fixture
def circle(admin):
    """Membership for the creator is auto-created by signal."""
    return Circle.objects.create(name="Edit Family", created_by=admin)


@pytest.fixture
def poster(circle):
    """A plain member who posted the keep."""
    user = User.objects.create_user(email="edit-poster@example.com", password="posterpass123")
    CircleMembership.objects.create(user=user, circle=circle, role=UserRole.CIRCLE_MEMBER)
    return user


@pytest.fixture
def member(circle):
    """Another plain member: neither the poster nor an admin."""
    user = User.objects.create_user(email="edit-member@example.com", password="memberpass123")
    CircleMembership.objects.create(user=user, circle=circle, role=UserRole.CIRCLE_MEMBER)
    return user


@pytest.fixture
def outsider():
    return User.objects.create_user(email="edit-outsider@example.com", password="outsiderpass123")


@pytest.fixture
def other_circle(outsider):
    return Circle.objects.create(name="Other Family", created_by=outsider)


@pytest.fixture
def keep(circle, poster):
    return Keep.objects.create(
        circle=circle,
        created_by=poster,
        keep_type=KeepType.NOTE,
        title="Beach day",
        description="Sand everywhere",
        date_of_memory=BASE_TIME,
    )


@pytest.fixture
def jo(circle):
    return Person.objects.create(circle=circle, name="Grandma Jo")


@pytest.fixture
def ana(circle):
    return Person.objects.create(circle=circle, name="Aunt Ana")


EDIT = {
    "title": "Lake day",
    "description": "Cold water",
    "date_of_memory": "2026-06-15T12:00:00Z",
}


@pytest.mark.django_db
class TestEditKeep:
    def test_poster_edits_title_caption_date_and_people(self, api_client, poster, keep, jo, ana):
        KeepPerson.objects.create(keep=keep, person=jo)
        api_client.force_authenticate(user=poster)

        response = api_client.patch(keep_url(keep.id), {**EDIT, "people": [str(ana.id)]}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["title"] == "Lake day"
        keep.refresh_from_db()
        assert keep.title == "Lake day"
        assert keep.description == "Cold water"
        assert keep.date_of_memory == datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc)
        assert tagged(keep) == {"Aunt Ana"}
        assert KeepPerson.objects.get(keep=keep).added_by == poster

    def test_admin_edits_a_members_post(self, api_client, admin, keep, jo):
        api_client.force_authenticate(user=admin)

        response = api_client.patch(keep_url(keep.id), {**EDIT, "people": [str(jo.id)]}, format="json")

        assert response.status_code == status.HTTP_200_OK
        keep.refresh_from_db()
        assert keep.title == "Lake day"
        assert tagged(keep) == {"Grandma Jo"}

    def test_another_member_is_forbidden(self, api_client, member, keep, jo):
        api_client.force_authenticate(user=member)

        response = api_client.patch(keep_url(keep.id), {**EDIT, "people": [str(jo.id)]}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        keep.refresh_from_db()
        assert keep.title == "Beach day"
        assert tagged(keep) == set()

    def test_someone_outside_the_circle_gets_a_404(self, api_client, outsider, keep):
        api_client.force_authenticate(user=outsider)

        response = api_client.patch(keep_url(keep.id), EDIT, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        keep.refresh_from_db()
        assert keep.title == "Beach day"

    def test_people_must_be_from_the_posts_circle(self, api_client, poster, keep, jo, other_circle):
        stranger = Person.objects.create(circle=other_circle, name="Stranger")
        KeepPerson.objects.create(keep=keep, person=jo)
        api_client.force_authenticate(user=poster)

        response = api_client.patch(
            keep_url(keep.id), {**EDIT, "people": [str(jo.id), str(stranger.id)]}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        keep.refresh_from_db()
        assert keep.title == "Beach day"
        assert tagged(keep) == {"Grandma Jo"}

    def test_unknown_or_malformed_person_ids_are_rejected(self, api_client, poster, keep):
        api_client.force_authenticate(user=poster)

        for people in (["00000000-0000-0000-0000-000000000000"], ["nope"]):
            response = api_client.patch(keep_url(keep.id), {"people": people}, format="json")
            assert response.status_code == status.HTTP_400_BAD_REQUEST, people

    def test_an_empty_list_untags_everyone(self, api_client, poster, keep, jo):
        KeepPerson.objects.create(keep=keep, person=jo)
        api_client.force_authenticate(user=poster)

        response = api_client.patch(keep_url(keep.id), {"people": []}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert tagged(keep) == set()

    def test_leaving_people_out_keeps_the_tags(self, api_client, poster, keep, jo):
        KeepPerson.objects.create(keep=keep, person=jo)
        api_client.force_authenticate(user=poster)

        response = api_client.patch(keep_url(keep.id), {"title": "Only the title"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert tagged(keep) == {"Grandma Jo"}

    def test_tagging_a_childs_person_links_the_child(self, api_client, poster, keep, circle):
        sophia = ChildProfile.objects.create(circle=circle, display_name="Sophia M")
        person = Person.objects.create(circle=circle, child=sophia, name="Sophia M")
        api_client.force_authenticate(user=poster)

        response = api_client.patch(keep_url(keep.id), {"people": [str(person.id)]}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert list(keep.children.all()) == [sophia]

    def test_the_post_stays_in_its_circle(self, api_client, poster, keep, circle, other_circle):
        api_client.force_authenticate(user=poster)

        response = api_client.patch(keep_url(keep.id), {"circle": other_circle.id, "title": "Moved?"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        keep.refresh_from_db()
        assert keep.circle == circle
        assert keep.title == "Moved?"

    def test_the_feed_shows_the_edit(self, api_client, poster, keep, ana):
        api_client.force_authenticate(user=poster)
        api_client.patch(keep_url(keep.id), {**EDIT, "people": [str(ana.id)]}, format="json")

        item = api_client.get(f"/api/keeps/feed/{keep.id}/").data

        assert item["title"] == "Lake day"
        assert item["description"] == "Cold water"
        assert item["date_of_memory"].startswith("2026-06-15")
        assert item["people"] == [{"id": str(ana.id), "name": "Aunt Ana"}]
        assert item["can_delete"] is True
