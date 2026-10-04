"""Tagging people on posts: the models, the children mirror, the backfill, the feed and the people API."""

from datetime import datetime, timedelta, timezone
from importlib import import_module

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, transaction
from django.test.utils import CaptureQueriesContext
from rest_framework import status
from rest_framework.test import APIClient

from mysite.circles.models import Circle, CircleMembership
from mysite.keeps.models import Keep, KeepPerson, KeepType, Person
from mysite.users.models import ChildProfile, PetProfile, PetType

User = get_user_model()

FEED_URL = "/api/keeps/feed/"
KEEPS_URL = "/api/keeps/"
BASE_TIME = datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc)


def tag_url(keep_id):
    return f"/api/keeps/feed/{keep_id}/people/"


def circle_people_url(circle_id):
    return f"/api/keeps/circles/{circle_id}/people/"


def person_url(person_id):
    return f"/api/keeps/people/{person_id}/"


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user():
    return User.objects.create_user(
        email="people@example.com", password="testpass123", first_name="Leo", last_name="Merza"
    )


@pytest.fixture
def circle(user):
    """Membership for the creator is auto-created by signal."""
    return Circle.objects.create(name="People Family", created_by=user)


@pytest.fixture
def member(circle):
    """Another member of the circle; not the posts' creator or an admin."""
    other = User.objects.create_user(email="people-member@example.com", password="memberpass123", first_name="Ana")
    CircleMembership.objects.create(user=other, circle=circle)
    return other


@pytest.fixture
def outsider():
    return User.objects.create_user(email="people-outsider@example.com", password="outsiderpass123")


@pytest.fixture
def other_circle(outsider):
    return Circle.objects.create(name="Other Family", created_by=outsider)


@pytest.fixture
def sophia(circle):
    return ChildProfile.objects.create(
        circle=circle, display_name="Sophia M", pending_invite_email="secret-invite@example.com"
    )


def make_keep(circle, user, when=BASE_TIME, *, title="Memory"):
    # Text posts always show in the feed, so no media is needed.
    return Keep.objects.create(
        circle=circle, created_by=user, keep_type=KeepType.NOTE, title=title, date_of_memory=when
    )


def free_person(circle, name):
    return Person.objects.create(circle=circle, name=name)


def tagged(keep):
    return set(KeepPerson.objects.filter(keep=keep).values_list("person__name", flat=True))


@pytest.mark.django_db
class TestPersonModel:
    def test_one_person_per_child_user_and_pet_in_a_circle(self, circle, user, sophia):
        pet = PetProfile.objects.create(circle=circle, name="Rex", pet_type=PetType.DOG)
        for link in ({"child": sophia}, {"user": user}, {"pet": pet}):
            Person.objects.create(circle=circle, name="First", **link)
            with pytest.raises(IntegrityError), transaction.atomic():
                Person.objects.create(circle=circle, name="Second", **link)

    def test_the_same_child_can_be_a_person_in_another_circle(self, circle, other_circle, sophia):
        Person.objects.create(circle=circle, child=sophia, name="Sophia M")
        Person.objects.create(circle=other_circle, child=sophia, name="Sophia M")

        assert Person.objects.filter(child=sophia).count() == 2

    def test_free_text_names_are_unique_per_circle_ignoring_case(self, circle, other_circle, sophia):
        free_person(circle, "Grandma Jo")
        with pytest.raises(IntegrityError), transaction.atomic():
            free_person(circle, "grandma jo")

        free_person(other_circle, "Grandma Jo")
        # A profile-linked person may share a free-text person's name.
        Person.objects.create(circle=circle, child=sophia, name="Grandma Jo")

    def test_kind_follows_the_link(self, circle, user, sophia):
        pet = PetProfile.objects.create(circle=circle, name="Rex", pet_type=PetType.DOG)

        assert Person(circle=circle, child=sophia).kind == "child"
        assert Person(circle=circle, user=user).kind == "member"
        assert Person(circle=circle, pet=pet).kind == "pet"
        assert Person(circle=circle, name="Grandma Jo").kind == "other"

    def test_a_person_is_tagged_once_per_post(self, circle, user):
        keep = make_keep(circle, user)
        jo = free_person(circle, "Grandma Jo")
        KeepPerson.objects.create(keep=keep, person=jo)
        with pytest.raises(IntegrityError), transaction.atomic():
            KeepPerson.objects.create(keep=keep, person=jo)


@pytest.mark.django_db
class TestChildrenMirror:
    """``Keep.children`` (written by the Tinybeans importer) is mirrored into people tags."""

    def test_linking_a_child_tags_their_person(self, circle, user, sophia):
        keep = make_keep(circle, user)

        keep.children.add(sophia)

        person = Person.objects.get(circle=circle, child=sophia)
        assert person.name == "Sophia M"
        assert list(keep.people.all()) == [person]
        assert KeepPerson.objects.get(keep=keep).added_by is None

    def test_relinking_is_idempotent_and_reuses_the_person(self, circle, user, sophia):
        first, second = make_keep(circle, user), make_keep(circle, user)
        first.children.add(sophia)
        first.children.add(sophia)
        second.children.add(sophia)

        assert Person.objects.filter(child=sophia).count() == 1
        assert KeepPerson.objects.count() == 2

    def test_linking_from_the_child_side(self, circle, user, sophia):
        keep = make_keep(circle, user)

        sophia.keeps.add(keep)

        assert tagged(keep) == {"Sophia M"}

    def test_unlinking_or_clearing_untags_but_keeps_the_person(self, circle, user, sophia):
        keep = make_keep(circle, user)
        jo = free_person(circle, "Grandma Jo")
        KeepPerson.objects.create(keep=keep, person=jo)
        keep.children.add(sophia)

        keep.children.remove(sophia)
        assert tagged(keep) == {"Grandma Jo"}

        keep.children.add(sophia)
        keep.children.clear()
        assert tagged(keep) == {"Grandma Jo"}

        keep.children.add(sophia)
        sophia.keeps.remove(keep)
        assert tagged(keep) == {"Grandma Jo"}
        assert Person.objects.filter(child=sophia).exists()


@pytest.mark.django_db
class TestBackfillMigration:
    def test_copies_child_links_into_people(self, circle, other_circle, user, outsider, sophia):
        aubrey = ChildProfile.objects.create(circle=circle, display_name="Aubrey Merza")
        ChildProfile.objects.create(circle=circle, display_name="No Posts")
        first, second = make_keep(circle, user), make_keep(circle, user)
        elsewhere = make_keep(other_circle, outsider)
        existing = Person.objects.create(circle=circle, child=aubrey, name="Aubs")
        # Write the links straight to the table, as before the mirror existed.
        Link = Keep.children.through
        Link.objects.bulk_create(
            [
                Link(keep=first, childprofile=sophia),
                Link(keep=first, childprofile=aubrey),
                Link(keep=second, childprofile=sophia),
                Link(keep=elsewhere, childprofile=sophia),
            ]
        )
        assert not KeepPerson.objects.exists()
        migration = import_module("mysite.keeps.migrations.0015_backfill_people_from_children")

        migration.backfill_people_from_children(apps, None)
        migration.backfill_people_from_children(apps, None)  # idempotent

        assert tagged(first) == {"Sophia M", "Aubs"}
        assert KeepPerson.objects.filter(keep=first, person=existing).exists()  # reused, not duplicated
        assert tagged(second) == {"Sophia M"}
        assert tagged(elsewhere) == {"Sophia M"}
        assert Person.objects.filter(child=sophia).count() == 2  # one per circle
        assert Person.objects.get(circle=other_circle, child=sophia).name == "Sophia M"
        assert not Person.objects.filter(name="No Posts").exists()
        assert KeepPerson.objects.count() == 4


@pytest.mark.django_db
class TestFeedPeople:
    def test_feed_lists_people_in_name_order(self, api_client, circle, user):
        keep = make_keep(circle, user)
        make_keep(circle, user, BASE_TIME - timedelta(days=1), title="Untagged")
        for name in ("zed", "Ann", "bob"):
            KeepPerson.objects.create(keep=keep, person=free_person(circle, name))
        api_client.force_authenticate(user=user)

        results = api_client.get(FEED_URL).data["results"]

        assert [p["name"] for p in results[0]["people"]] == ["Ann", "bob", "zed"]
        assert set(results[0]["people"][0]) == {"id", "name"}
        assert results[1]["people"] == []

    def test_query_count_does_not_grow_with_people(self, api_client, circle, user):
        api_client.force_authenticate(user=user)
        keep = make_keep(circle, user)
        KeepPerson.objects.create(keep=keep, person=free_person(circle, "First"))
        with CaptureQueriesContext(connection) as small:
            api_client.get(FEED_URL)

        for n in range(5):
            more = make_keep(circle, user, BASE_TIME + timedelta(minutes=n + 1))
            for m in range(3):
                KeepPerson.objects.create(keep=more, person=free_person(circle, f"P{n}-{m}"))
        with CaptureQueriesContext(connection) as large:
            api_client.get(FEED_URL)

        assert len(large.captured_queries) == len(small.captured_queries)

    def test_filters_by_person_newest_first_without_duplicates(self, api_client, circle, user):
        jo, ann = free_person(circle, "Grandma Jo"), free_person(circle, "Ann")
        older = make_keep(circle, user, BASE_TIME - timedelta(days=2), title="Older")
        newer = make_keep(circle, user, BASE_TIME, title="Newer")
        make_keep(circle, user, BASE_TIME - timedelta(days=1), title="Not Jo")
        for keep in (older, newer):
            KeepPerson.objects.create(keep=keep, person=jo)
            KeepPerson.objects.create(keep=keep, person=ann)
        api_client.force_authenticate(user=user)

        response = api_client.get(FEED_URL, {"person": str(jo.id)})

        assert response.status_code == status.HTTP_200_OK
        assert [item["title"] for item in response.data["results"]] == ["Newer", "Older"]

    def test_person_filter_pages_with_the_cursor(self, api_client, circle, user):
        jo = free_person(circle, "Grandma Jo")
        for n in range(3):
            KeepPerson.objects.create(
                keep=make_keep(circle, user, BASE_TIME - timedelta(days=n), title=f"Day {n}"), person=jo
            )
        api_client.force_authenticate(user=user)

        first = api_client.get(FEED_URL, {"person": str(jo.id), "page_size": 2}).data
        second = api_client.get(first["next"]).data

        assert [item["title"] for item in first["results"] + second["results"]] == ["Day 0", "Day 1", "Day 2"]

    def test_bad_person_id_is_a_400(self, api_client, user):
        api_client.force_authenticate(user=user)

        assert api_client.get(FEED_URL, {"person": "nope"}).status_code == status.HTTP_400_BAD_REQUEST

    def test_a_person_from_another_circle_shows_nothing(self, api_client, circle, user, other_circle, outsider):
        stranger = free_person(other_circle, "Stranger")
        KeepPerson.objects.create(keep=make_keep(other_circle, outsider), person=stranger)
        make_keep(circle, user)
        api_client.force_authenticate(user=user)

        response = api_client.get(FEED_URL, {"person": str(stranger.id)})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["results"] == []


@pytest.mark.django_db
class TestSetKeepPeople:
    def test_any_member_can_tag_and_gets_the_new_list(self, api_client, circle, user, member):
        keep = make_keep(circle, user)
        jo, ann = free_person(circle, "Grandma Jo"), free_person(circle, "ann")
        api_client.force_authenticate(user=member)

        response = api_client.patch(tag_url(keep.id), {"people": [str(jo.id), str(ann.id)]}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data == {
            "people": [{"id": str(ann.id), "name": "ann"}, {"id": str(jo.id), "name": "Grandma Jo"}]
        }
        assert KeepPerson.objects.get(keep=keep, person=jo).added_by == member

    def test_replaces_the_whole_list(self, api_client, circle, user):
        keep = make_keep(circle, user)
        jo, ann = free_person(circle, "Grandma Jo"), free_person(circle, "Ann")
        KeepPerson.objects.create(keep=keep, person=jo)
        api_client.force_authenticate(user=user)

        api_client.patch(tag_url(keep.id), {"people": [str(ann.id)]}, format="json")
        assert tagged(keep) == {"Ann"}

        response = api_client.patch(tag_url(keep.id), {"people": []}, format="json")
        assert response.data == {"people": []}
        assert tagged(keep) == set()

    def test_keeps_child_links_in_step(self, api_client, circle, user, sophia):
        keep = make_keep(circle, user)
        sophia_person = Person.objects.create(circle=circle, child=sophia, name="Sophia M")
        jo = free_person(circle, "Grandma Jo")
        api_client.force_authenticate(user=user)

        api_client.patch(tag_url(keep.id), {"people": [str(sophia_person.id), str(jo.id)]}, format="json")
        assert list(keep.children.all()) == [sophia]
        assert tagged(keep) == {"Sophia M", "Grandma Jo"}
        assert KeepPerson.objects.get(keep=keep, person=sophia_person).added_by == user

        api_client.patch(tag_url(keep.id), {"people": [str(jo.id)]}, format="json")
        assert list(keep.children.all()) == []
        assert tagged(keep) == {"Grandma Jo"}

    def test_non_member_gets_404(self, api_client, circle, user, outsider):
        keep = make_keep(circle, user)
        jo = free_person(circle, "Grandma Jo")
        api_client.force_authenticate(user=outsider)

        response = api_client.patch(tag_url(keep.id), {"people": [str(jo.id)]}, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert tagged(keep) == set()

    def test_person_from_another_circle_is_rejected(self, api_client, circle, user, other_circle):
        keep = make_keep(circle, user)
        jo = free_person(circle, "Grandma Jo")
        KeepPerson.objects.create(keep=keep, person=jo)
        stranger = free_person(other_circle, "Stranger")
        api_client.force_authenticate(user=user)

        response = api_client.patch(tag_url(keep.id), {"people": [str(stranger.id)]}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert tagged(keep) == {"Grandma Jo"}

    def test_invalid_body_is_rejected(self, api_client, circle, user):
        keep = make_keep(circle, user)
        api_client.force_authenticate(user=user)

        assert api_client.patch(tag_url(keep.id), {"people": ["x"]}, format="json").status_code == 400
        assert api_client.patch(tag_url(keep.id), {}, format="json").status_code == 400

    def test_requires_authentication(self, api_client, circle, user):
        keep = make_keep(circle, user)

        response = api_client.patch(tag_url(keep.id), {"people": []}, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestCirclePeople:
    def test_lists_children_members_pets_and_free_text_people(self, api_client, circle, user, member, sophia):
        PetProfile.objects.create(circle=circle, name="Rex", pet_type=PetType.DOG)
        jo = free_person(circle, "Grandma Jo")
        api_client.force_authenticate(user=member)

        response = api_client.get(circle_people_url(circle.id))

        assert response.status_code == status.HTTP_200_OK
        assert [(p["name"], p["kind"]) for p in response.data] == [
            ("Ana", "member"),
            ("Grandma Jo", "other"),
            ("Leo Merza", "member"),
            ("Rex", "pet"),
            ("Sophia M", "child"),
        ]
        assert next(p for p in response.data if p["name"] == "Grandma Jo")["id"] == str(jo.id)
        # Nothing about the linked profiles leaks out.
        assert all(set(p) == {"id", "name", "kind"} for p in response.data)
        assert "secret-invite" not in str(response.content)

    def test_listing_again_creates_no_duplicates(self, api_client, circle, user, sophia):
        api_client.force_authenticate(user=user)

        first = api_client.get(circle_people_url(circle.id)).data
        second = api_client.get(circle_people_url(circle.id)).data

        assert first == second
        assert Person.objects.filter(circle=circle).count() == 2

    def test_non_member_gets_404(self, api_client, circle, outsider):
        api_client.force_authenticate(user=outsider)

        assert api_client.get(circle_people_url(circle.id)).status_code == status.HTTP_404_NOT_FOUND
        response = api_client.post(circle_people_url(circle.id), {"name": "Grandma Jo"}, format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert not Person.objects.exists()

    def test_any_member_can_add_a_free_text_person(self, api_client, circle, member):
        api_client.force_authenticate(user=member)

        response = api_client.post(circle_people_url(circle.id), {"name": "  Grandma Jo  "}, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        person = Person.objects.get(id=response.data["id"])
        assert response.data == {"id": str(person.id), "name": "Grandma Jo", "kind": "other"}
        assert (person.circle, person.created_by) == (circle, member)

    def test_rejects_duplicate_blank_and_too_long_names(self, api_client, circle, user, sophia):
        free_person(circle, "Grandma Jo")
        api_client.force_authenticate(user=user)

        for name in ("grandma JO", "   ", "x" * 151):
            response = api_client.post(circle_people_url(circle.id), {"name": name}, format="json")
            assert response.status_code == status.HTTP_400_BAD_REQUEST, name
        # Only other free-text people count as duplicates.
        response = api_client.post(circle_people_url(circle.id), {"name": "Sophia M"}, format="json")
        assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
class TestPersonDetail:
    def test_member_sees_the_person_and_circle(self, api_client, circle, member, sophia):
        person = Person.objects.create(circle=circle, child=sophia, name="Sophia M")
        api_client.force_authenticate(user=member)

        response = api_client.get(person_url(person.id))

        assert response.status_code == status.HTTP_200_OK
        assert response.data == {
            "id": str(person.id),
            "name": "Sophia M",
            "kind": "child",
            "circle": {"id": circle.id, "name": circle.name, "slug": circle.slug},
        }

    def test_non_member_gets_404(self, api_client, circle, outsider):
        person = free_person(circle, "Grandma Jo")
        api_client.force_authenticate(user=outsider)

        assert api_client.get(person_url(person.id)).status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestCreatePostWithPeople:
    def test_tags_people_and_links_children(self, api_client, circle, user, sophia):
        sophia_person = Person.objects.create(circle=circle, child=sophia, name="Sophia M")
        jo = free_person(circle, "Grandma Jo")
        api_client.force_authenticate(user=user)

        response = api_client.post(
            KEEPS_URL,
            {"circle": circle.id, "keep_type": "media", "people": [str(sophia_person.id), str(jo.id)]},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        keep = Keep.objects.get(id=response.data["id"])
        assert tagged(keep) == {"Sophia M", "Grandma Jo"}
        assert list(keep.children.all()) == [sophia]
        assert KeepPerson.objects.filter(keep=keep, added_by=user).count() == 2

    def test_rejects_people_from_another_circle(self, api_client, circle, user, other_circle):
        stranger = free_person(other_circle, "Stranger")
        api_client.force_authenticate(user=user)

        response = api_client.post(
            KEEPS_URL, {"circle": circle.id, "keep_type": "media", "people": [str(stranger.id)]}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not Keep.objects.exists()
