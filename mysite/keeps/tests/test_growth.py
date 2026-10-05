"""A child's growth log: the model's checks and the admin-only API."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from mysite.circles.models import Circle, CircleMembership
from mysite.keeps.models import GrowthMeasurement, Person
from mysite.users.models import ChildProfile

User = get_user_model()


def growth_url(person_id):
    return f"/api/keeps/people/{person_id}/growth/"


def measurement_url(person_id, measurement_id):
    return f"/api/keeps/people/{person_id}/growth/{measurement_id}/"


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin():
    """Creates the circle, so the signal makes them its admin."""
    return User.objects.create_user(email="growth-admin@example.com", password="adminpass123")


@pytest.fixture
def circle(admin):
    return Circle.objects.create(name="Growth Family", created_by=admin)


@pytest.fixture
def member(circle):
    user = User.objects.create_user(email="growth-member@example.com", password="memberpass123")
    CircleMembership.objects.create(user=user, circle=circle)
    return user


@pytest.fixture
def outsider():
    return User.objects.create_user(email="growth-outsider@example.com", password="outsiderpass123")


@pytest.fixture
def child(circle):
    return ChildProfile.objects.create(circle=circle, display_name="Sophia M", birthdate=date(2025, 1, 15))


@pytest.fixture
def person(circle, child):
    return Person.objects.create(circle=circle, child=child, name="Sophia M")


def measure(person, when=date(2025, 6, 1), *, height=None, weight=None):
    return GrowthMeasurement.objects.create(person=person, measured_on=when, height_cm=height, weight_kg=weight)


@pytest.mark.django_db
class TestGrowthMeasurementModel:
    def test_needs_a_height_or_a_weight(self, person):
        measurement = GrowthMeasurement(person=person, measured_on=date(2025, 6, 1))
        with pytest.raises(ValidationError) as error:
            measurement.full_clean()
        assert "height_cm" in error.value.message_dict

        # The database refuses it too.
        with pytest.raises(IntegrityError), transaction.atomic():
            measurement.save()

    def test_either_one_alone_is_enough(self, person):
        GrowthMeasurement(person=person, measured_on=date(2025, 6, 1), height_cm=Decimal("61.5")).full_clean()
        GrowthMeasurement(person=person, measured_on=date(2025, 6, 1), weight_kg=Decimal("6.250")).full_clean()

    def test_only_for_a_child(self, circle, admin):
        member_person = Person.objects.create(circle=circle, user=admin, name="Leo")
        measurement = GrowthMeasurement(person=member_person, measured_on=date(2025, 6, 1), height_cm=Decimal("170"))
        with pytest.raises(ValidationError) as error:
            measurement.full_clean()
        assert "person" in error.value.message_dict

    def test_rejects_future_dates_and_dates_before_birth(self, person):
        future = GrowthMeasurement(
            person=person, measured_on=timezone.localdate() + timedelta(days=3), weight_kg=Decimal("5")
        )
        before_birth = GrowthMeasurement(person=person, measured_on=date(2025, 1, 14), weight_kg=Decimal("3"))
        for measurement in (future, before_birth):
            with pytest.raises(ValidationError) as error:
                measurement.full_clean()
            assert "measured_on" in error.value.message_dict

    def test_rejects_out_of_range_values(self, person):
        for values in ({"height_cm": Decimal("0")}, {"height_cm": Decimal("300")}, {"weight_kg": Decimal("0")}):
            with pytest.raises(ValidationError):
                GrowthMeasurement(person=person, measured_on=date(2025, 6, 1), **values).full_clean()

    def test_deleted_with_the_person(self, person):
        measure(person, weight=Decimal("5"))
        person.delete()
        assert not GrowthMeasurement.objects.exists()


@pytest.mark.django_db
class TestGrowthRead:
    def test_member_reads_the_log_oldest_first(self, api_client, member, person):
        later = measure(person, date(2025, 9, 1), height=Decimal("70.2"), weight=Decimal("8.125"))
        earlier = measure(person, date(2025, 3, 1), weight=Decimal("5.4"))
        api_client.force_authenticate(member)

        response = api_client.get(growth_url(person.id))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["can_edit"] is False
        assert str(response.data["birthdate"]) == "2025-01-15"
        rows = response.data["measurements"]
        assert [row["id"] for row in rows] == [str(earlier.id), str(later.id)]
        # Numbers, not strings.
        assert rows[1]["height_cm"] == Decimal("70.2")
        assert response.json()["measurements"][1]["weight_kg"] == 8.125
        assert rows[0]["height_cm"] is None

    def test_admin_may_edit(self, api_client, admin, person):
        api_client.force_authenticate(admin)
        response = api_client.get(growth_url(person.id))
        assert response.data["can_edit"] is True

    def test_outsider_gets_404(self, api_client, outsider, person):
        measure(person, weight=Decimal("5"))
        api_client.force_authenticate(outsider)

        assert api_client.get(growth_url(person.id)).status_code == status.HTTP_404_NOT_FOUND
        response = api_client.post(growth_url(person.id), {"measured_on": "2025-06-01", "weight_kg": 5}, format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_non_child_people_have_no_log(self, api_client, admin, circle):
        grandma = Person.objects.create(circle=circle, name="Grandma Jo")
        api_client.force_authenticate(admin)
        assert api_client.get(growth_url(grandma.id)).status_code == status.HTTP_404_NOT_FOUND

    def test_requires_login(self, api_client, person):
        assert api_client.get(growth_url(person.id)).status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestGrowthWrite:
    def test_admin_logs_a_measurement(self, api_client, admin, person):
        api_client.force_authenticate(admin)

        response = api_client.post(
            growth_url(person.id),
            {"measured_on": "2025-06-01", "height_cm": 61.5, "weight_kg": 6.25, "note": "4 month checkup"},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        measurement = GrowthMeasurement.objects.get()
        assert measurement.person == person
        assert measurement.created_by == admin
        assert measurement.height_cm == Decimal("61.5")
        assert measurement.weight_kg == Decimal("6.250")
        assert measurement.note == "4 month checkup"

    def test_values_are_rounded_to_the_stored_precision(self, api_client, admin, person):
        api_client.force_authenticate(admin)
        # 20.25 in and 13 lb 13 oz, converted on the client.
        response = api_client.post(
            growth_url(person.id),
            {"measured_on": "2025-06-01", "height_cm": 51.435, "weight_kg": 6.26524},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        measurement = GrowthMeasurement.objects.get()
        assert measurement.height_cm == Decimal("51.4")
        assert measurement.weight_kg == Decimal("6.265")

    def test_member_cannot_add_change_or_delete(self, api_client, member, person):
        measurement = measure(person, weight=Decimal("5"))
        api_client.force_authenticate(member)

        responses = [
            api_client.post(growth_url(person.id), {"measured_on": "2025-06-01", "weight_kg": 6}, format="json"),
            api_client.patch(measurement_url(person.id, measurement.id), {"weight_kg": 6}, format="json"),
            api_client.delete(measurement_url(person.id, measurement.id)),
        ]

        assert [response.status_code for response in responses] == [status.HTTP_403_FORBIDDEN] * 3
        measurement.refresh_from_db()
        assert measurement.weight_kg == Decimal("5.000")
        assert GrowthMeasurement.objects.count() == 1

    def test_needs_height_or_weight(self, api_client, admin, person):
        api_client.force_authenticate(admin)
        response = api_client.post(growth_url(person.id), {"measured_on": "2025-06-01"}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not GrowthMeasurement.objects.exists()

    def test_rejects_a_date_before_birth(self, api_client, admin, person):
        api_client.force_authenticate(admin)
        response = api_client.post(growth_url(person.id), {"measured_on": "2024-12-31", "weight_kg": 3}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_admin_changes_only_what_is_sent(self, api_client, admin, person):
        measurement = measure(person, height=Decimal("61.5"), weight=Decimal("6.250"))
        api_client.force_authenticate(admin)

        response = api_client.patch(measurement_url(person.id, measurement.id), {"weight_kg": 6.3}, format="json")

        assert response.status_code == status.HTTP_200_OK
        measurement.refresh_from_db()
        assert measurement.height_cm == Decimal("61.5")
        assert measurement.weight_kg == Decimal("6.300")

    def test_cannot_clear_both_values(self, api_client, admin, person):
        measurement = measure(person, weight=Decimal("6.250"))
        api_client.force_authenticate(admin)

        response = api_client.patch(measurement_url(person.id, measurement.id), {"weight_kg": None}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        measurement.refresh_from_db()
        assert measurement.weight_kg == Decimal("6.250")

    def test_admin_deletes(self, api_client, admin, person):
        measurement = measure(person, weight=Decimal("5"))
        api_client.force_authenticate(admin)

        response = api_client.delete(measurement_url(person.id, measurement.id))

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not GrowthMeasurement.objects.exists()

    def test_measurement_of_another_person_is_404(self, api_client, admin, circle, person):
        sibling = Person.objects.create(
            circle=circle, child=ChildProfile.objects.create(circle=circle, display_name="Max"), name="Max"
        )
        measurement = measure(sibling, weight=Decimal("5"))
        api_client.force_authenticate(admin)

        response = api_client.delete(measurement_url(person.id, measurement.id))

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert GrowthMeasurement.objects.count() == 1

    def test_admin_of_another_circle_cannot_write(self, api_client, outsider, person):
        Circle.objects.create(name="Other Family", created_by=outsider)
        api_client.force_authenticate(outsider)

        response = api_client.post(growth_url(person.id), {"measured_on": "2025-06-01", "weight_kg": 5}, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND
