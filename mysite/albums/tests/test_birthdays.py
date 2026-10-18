"""Tests for the Birthdays album: spotting birthday posts, the sync, deleting it, the setting and child birthdates."""

from datetime import date, datetime
from datetime import timezone as dt_timezone
from unittest.mock import patch

import pytest
from django.conf import settings
from django.urls import reverse
from rest_framework import status

from mysite.albums.birthdays import (
    ALBUM_NAME,
    anniversary,
    birthday_keeps,
    is_birthday_caption,
    sync_birthday_album,
    sync_enabled_circles,
)
from mysite.albums.models import Album, AlbumKeep, BirthdayAlbum, BirthdayAlbumMatch
from mysite.albums.tasks import sync_birthday_albums
from mysite.circles.models import Circle
from mysite.users.models import ChildProfile

from .helpers import make_album, make_keep

TODAY = date(2026, 10, 18)


def at(day: date, hour=12) -> datetime:
    return datetime(day.year, day.month, day.day, hour, tzinfo=dt_timezone.utc)


def enable(circle):
    Circle.objects.filter(pk=circle.pk).update(birthday_album_enabled=True)
    circle.refresh_from_db()


def album_titles(album):
    return list(album.album_keeps.order_by("keep__date_of_memory").values_list("keep__title", flat=True))


@pytest.fixture
def sophia(circle):
    return ChildProfile.objects.create(circle=circle, display_name="Sophia", birthdate=date(2023, 10, 16))


@pytest.fixture
def aubrey(circle):
    return ChildProfile.objects.create(circle=circle, display_name="Aubrey", birthdate=date(2026, 6, 10))


@pytest.fixture
def verified_admin(admin):
    admin.email_verified = True
    admin.save(update_fields=["email_verified"])
    return admin


@pytest.fixture
def verified_member(member):
    member.email_verified = True
    member.save(update_fields=["email_verified"])
    return member


class TestIsBirthdayCaption:
    @pytest.mark.parametrize(
        "text",
        [
            "1st birthday",
            "Sophia's 2nd birthday party time!",
            "Birthday girl",
            "Happy bday!",
            "b-day cake",
            "#happybirthday",
            "Sophia turns 3 today",
            "Turned two!",
            "12 month birthday!",
            "Aubrey's 4 month birthday and Sophia's 3rd birthday",
            "Feliz cumpleaños",
        ],
    )
    def test_birthday_posts(self, text):
        assert is_birthday_caption(text)

    @pytest.mark.parametrize(
        "text",
        [
            "",
            "Park day",
            "1 month birthday!",
            "4 months birthday",
            "Six-month bday",
            "3 weeks old birthday",
            "Happy half birthday",
            "She turns 4 months today",
            "Today is a good day",
        ],
    )
    def test_not_birthday_posts(self, text):
        assert not is_birthday_caption(text)

    def test_leap_day_birthdays_fall_on_feb_28(self):
        assert anniversary(date(2024, 2, 29), 2025) == date(2025, 2, 28)
        assert anniversary(date(2024, 2, 29), 2028) == date(2028, 2, 29)


@pytest.mark.django_db
class TestBirthdayKeeps:
    def test_real_family_posts(self, circle, admin, sophia, aubrey):
        make_keep(circle, admin, at(date(2024, 10, 16)), title="1st birthday")
        make_keep(circle, admin, at(date(2025, 10, 18)), title="Sophia's 2nd birthday party time!")
        # Monthly milestones, one of them inside Sophia's birthday window.
        make_keep(circle, admin, at(date(2026, 7, 10)), title="1 month birthday!")
        make_keep(circle, admin, at(date(2026, 10, 10)), title="4 month birthday!")
        # Near a birthday but not about one, and about a birthday far from any child's.
        make_keep(circle, admin, at(date(2025, 10, 17)), title="Park day")
        make_keep(circle, admin, at(date(2025, 8, 1)), title="Grandma's birthday")
        # The day she was born isn't a birthday.
        make_keep(circle, admin, at(date(2023, 10, 16)), title="Happy birthday, welcome to the world")

        assert [keep.title for keep in birthday_keeps(circle, TODAY)] == [
            "1st birthday",
            "Sophia's 2nd birthday party time!",
        ]

    @pytest.mark.parametrize(
        ("when", "included"),
        [
            (datetime(2025, 10, 9, 0, 0, tzinfo=dt_timezone.utc), True),  # 7 days before
            (datetime(2025, 10, 8, 23, 59, tzinfo=dt_timezone.utc), False),
            (datetime(2025, 10, 30, 23, 59, tzinfo=dt_timezone.utc), True),  # 14 days after
            (datetime(2025, 10, 31, 0, 0, tzinfo=dt_timezone.utc), False),
        ],
    )
    def test_window_is_a_week_before_to_two_weeks_after(self, circle, admin, sophia, when, included):
        make_keep(circle, admin, when, title="Birthday")

        assert bool(birthday_keeps(circle, TODAY)) is included

    def test_matches_the_caption_too(self, circle, admin, sophia):
        keep = make_keep(circle, admin, at(date(2024, 10, 16)), title="")
        keep.description = "Cake time for her birthday"
        keep.save(update_fields=["description"])

        assert birthday_keeps(circle, TODAY) == [keep]

    def test_children_without_a_birthdate_are_skipped(self, circle, admin):
        ChildProfile.objects.create(circle=circle, display_name="No date")
        make_keep(circle, admin, at(date(2024, 10, 16)), title="1st birthday")

        assert birthday_keeps(circle, TODAY) == []

    def test_only_the_circles_own_children_and_posts(self, circle, admin, other_circle, outsider, sophia):
        make_keep(other_circle, outsider, at(date(2024, 10, 16)), title="1st birthday")
        ChildProfile.objects.create(circle=other_circle, display_name="Other", birthdate=date(2023, 3, 1))
        make_keep(circle, admin, at(date(2024, 3, 1)), title="1st birthday")

        assert birthday_keeps(circle, TODAY) == []


@pytest.mark.django_db
class TestSync:
    def test_does_nothing_while_turned_off(self, circle, admin, sophia):
        make_keep(circle, admin, at(date(2024, 10, 16)), title="1st birthday")

        assert sync_birthday_album(circle.id, TODAY) == 0
        assert not Album.objects.exists()

    def test_makes_the_album_oldest_first(self, circle, admin, sophia):
        enable(circle)
        make_keep(circle, admin, at(date(2025, 10, 18)), title="2nd birthday party")
        make_keep(circle, admin, at(date(2024, 10, 16)), title="1st birthday")

        assert sync_birthday_album(circle.id, TODAY) == 2

        album = Album.objects.get()
        assert (album.name, album.circle, album.created_by) == (ALBUM_NAME, circle, None)
        assert album_titles(album) == ["1st birthday", "2nd birthday party"]
        assert BirthdayAlbum.objects.get().album == album

    def test_no_birthday_posts_makes_no_album(self, circle, admin, sophia):
        enable(circle)
        make_keep(circle, admin, at(date(2024, 10, 16)), title="Park day")

        assert sync_birthday_album(circle.id, TODAY) == 0
        assert not Album.objects.exists()

    def test_rerun_adds_only_new_posts(self, circle, admin, sophia):
        enable(circle)
        make_keep(circle, admin, at(date(2024, 10, 16)), title="1st birthday")
        sync_birthday_album(circle.id, TODAY)
        album = Album.objects.get()
        Album.objects.filter(pk=album.pk).update(name="Sophia's birthdays", updated_at=at(date(2025, 1, 1)))

        assert sync_birthday_album(circle.id, TODAY) == 0
        make_keep(circle, admin, at(date(2025, 10, 16)), title="2nd birthday")
        assert sync_birthday_album(circle.id, TODAY) == 1

        album.refresh_from_db()
        assert Album.objects.count() == 1
        assert album.name == "Sophia's birthdays"
        assert album_titles(album) == ["1st birthday", "2nd birthday"]
        assert album.updated_at > at(date(2025, 1, 1))

    def test_a_post_an_admin_took_out_is_not_put_back(self, api_client, circle, admin, sophia):
        enable(circle)
        keep = make_keep(circle, admin, at(date(2024, 10, 16)), title="1st birthday")
        sync_birthday_album(circle.id, TODAY)
        album = Album.objects.get()
        api_client.force_authenticate(admin)

        response = api_client.delete(f"/api/albums/{album.id}/keeps/{keep.id}/")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert sync_birthday_album(circle.id, TODAY) == 0
        assert not AlbumKeep.objects.filter(album=album).exists()

    def test_a_post_an_admin_already_added_is_fine(self, circle, admin, sophia):
        enable(circle)
        keep = make_keep(circle, admin, at(date(2024, 10, 16)), title="1st birthday")
        make_keep(circle, admin, at(date(2025, 10, 16)), title="2nd birthday")
        sync_birthday_album(circle.id, date(2025, 1, 1))
        album = Album.objects.get()
        AlbumKeep.objects.filter(album=album).delete()
        BirthdayAlbumMatch.objects.all().delete()
        AlbumKeep.objects.create(album=album, keep=keep, added_by=admin)

        assert sync_birthday_album(circle.id, TODAY) == 2
        assert album.album_keeps.filter(keep=keep).count() == 1

    def test_a_child_birthdate_set_later_is_picked_up(self, circle, admin):
        enable(circle)
        child = ChildProfile.objects.create(circle=circle, display_name="Sophia")
        make_keep(circle, admin, at(date(2024, 10, 16)), title="1st birthday")
        assert sync_birthday_album(circle.id, TODAY) == 0

        child.birthdate = date(2023, 10, 16)
        child.save(update_fields=["birthdate"])

        assert sync_birthday_album(circle.id, TODAY) == 1

    def test_turning_it_off_keeps_the_album_and_stops_the_sync(self, circle, admin, sophia):
        enable(circle)
        make_keep(circle, admin, at(date(2024, 10, 16)), title="1st birthday")
        sync_birthday_album(circle.id, TODAY)
        Circle.objects.filter(pk=circle.pk).update(birthday_album_enabled=False)
        make_keep(circle, admin, at(date(2025, 10, 16)), title="2nd birthday")

        assert sync_birthday_album(circle.id, TODAY) == 0
        assert album_titles(Album.objects.get()) == ["1st birthday"]

    def test_only_enabled_circles_and_failures_are_reported(self, circle, admin, other_circle, outsider, sophia):
        enable(circle)
        enable(other_circle)
        make_keep(circle, admin, at(date(2024, 10, 16)), title="1st birthday")
        real = sync_birthday_album

        def flaky(circle_id, today=None):
            if circle_id == other_circle.id:
                raise RuntimeError("boom")
            return real(circle_id, today)

        with patch("mysite.albums.birthdays.sync_birthday_album", side_effect=flaky):
            assert sync_enabled_circles(today=TODAY) == (1, [other_circle.id])


@pytest.mark.django_db
class TestDeletingTheAlbum:
    def test_deleting_it_turns_the_setting_off_and_it_is_not_made_again(self, api_client, circle, admin, sophia):
        enable(circle)
        make_keep(circle, admin, at(date(2024, 10, 16)), title="1st birthday")
        sync_birthday_album(circle.id, TODAY)
        album = Album.objects.get()
        api_client.force_authenticate(admin)

        assert api_client.delete(f"/api/albums/{album.id}/").status_code == status.HTTP_204_NO_CONTENT

        circle.refresh_from_db()
        assert circle.birthday_album_enabled is False
        assert not BirthdayAlbum.objects.exists()
        assert not BirthdayAlbumMatch.objects.exists()
        assert sync_birthday_album(circle.id, TODAY) == 0
        assert not Album.objects.exists()

    def test_turning_it_back_on_starts_a_new_album(
        self, api_client, circle, verified_admin, sophia, django_capture_on_commit_callbacks
    ):
        enable(circle)
        make_keep(circle, verified_admin, at(date(2024, 10, 16)), title="1st birthday")
        sync_birthday_album(circle.id, TODAY)
        Album.objects.get().delete()
        api_client.force_authenticate(verified_admin)

        with django_capture_on_commit_callbacks(execute=True):
            api_client.patch(
                reverse("circle-detail", args=[circle.id]), {"birthday_album_enabled": True}, format="json"
            )

        assert album_titles(Album.objects.get()) == ["1st birthday"]

    def test_other_albums_and_circle_deletion_are_unaffected(self, circle, admin, sophia):
        enable(circle)
        make_album(circle, admin, name="Beach").delete()
        circle.refresh_from_db()
        assert circle.birthday_album_enabled is True

        make_keep(circle, admin, at(date(2024, 10, 16)), title="1st birthday")
        sync_birthday_album(circle.id, TODAY)
        circle.delete()
        assert not Album.objects.exists()


@pytest.mark.django_db
class TestBeatTask:
    def test_scheduled_nightly(self):
        entry = settings.CELERY_BEAT_SCHEDULE["sync-birthday-albums"]

        assert entry["task"] == sync_birthday_albums.name == "mysite.albums.tasks.sync_birthday_albums"
        assert entry["schedule"].hour == {7}
        assert entry["schedule"].minute == {30}

    def test_syncs_enabled_circles(self, circle, admin, sophia):
        enable(circle)
        make_keep(circle, admin, at(date(2024, 10, 16)), title="1st birthday")

        assert sync_birthday_albums.delay().get() == 1
        assert sync_birthday_albums.delay(circle_id=circle.id).get() == 0

    def test_retries_when_a_circle_fails(self, circle):
        with (
            patch("mysite.albums.tasks.sync_enabled_circles", return_value=(0, [circle.id])),
            patch.object(sync_birthday_albums, "retry", return_value=RuntimeError("retry")) as retry,
            pytest.raises(RuntimeError, match="retry"),
        ):
            sync_birthday_albums(circle_id=circle.id)
        retry.assert_called_once_with(kwargs={"circle_id": circle.id})


@pytest.mark.django_db
class TestSettingApi:
    def test_off_by_default(self, circle):
        assert circle.birthday_album_enabled is False

    def test_admin_turning_it_on_fills_the_album_right_away(
        self, api_client, circle, verified_admin, sophia, django_capture_on_commit_callbacks
    ):
        make_keep(circle, verified_admin, at(date(2024, 10, 16)), title="1st birthday")
        api_client.force_authenticate(verified_admin)

        with django_capture_on_commit_callbacks(execute=True) as callbacks:
            response = api_client.patch(
                reverse("circle-detail", args=[circle.id]), {"birthday_album_enabled": True}, format="json"
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["circle"]["birthday_album_enabled"] is True
        assert len(callbacks) == 1
        assert album_titles(Album.objects.get()) == ["1st birthday"]

    def test_saving_it_on_again_or_off_queues_nothing(
        self, api_client, circle, verified_admin, django_capture_on_commit_callbacks
    ):
        enable(circle)
        api_client.force_authenticate(verified_admin)
        url = reverse("circle-detail", args=[circle.id])

        with django_capture_on_commit_callbacks() as callbacks:
            api_client.patch(url, {"birthday_album_enabled": True}, format="json")
            api_client.patch(url, {"birthday_album_enabled": False}, format="json")

        assert callbacks == []
        circle.refresh_from_db()
        assert circle.birthday_album_enabled is False

    def test_members_cannot_turn_it_on(self, api_client, circle, verified_member):
        api_client.force_authenticate(verified_member)

        response = api_client.patch(
            reverse("circle-detail", args=[circle.id]), {"birthday_album_enabled": True}, format="json"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        circle.refresh_from_db()
        assert circle.birthday_album_enabled is False

    def test_shown_on_the_circle_settings_page(self, api_client, circle, verified_admin):
        enable(circle)
        api_client.force_authenticate(verified_admin)

        response = api_client.get(reverse("circle-member-list", args=[circle.id]))

        assert response.data["data"]["circle"]["birthday_album_enabled"] is True


@pytest.mark.django_db
class TestChildBirthdatesApi:
    def test_admin_lists_the_circles_children(self, api_client, circle, other_circle, verified_admin, sophia):
        ChildProfile.objects.create(circle=circle, display_name="Aubrey")
        ChildProfile.objects.create(circle=other_circle, display_name="Elsewhere", birthdate=date(2020, 1, 1))
        api_client.force_authenticate(verified_admin)

        response = api_client.get(reverse("circle-child-list", args=[circle.id]))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["children"] == [
            {"id": response.data["data"]["children"][0]["id"], "display_name": "Aubrey", "birthdate": None},
            {"id": str(sophia.id), "display_name": "Sophia", "birthdate": "2023-10-16"},
        ]

    def test_members_cannot_list_or_set(self, api_client, circle, verified_member, sophia):
        api_client.force_authenticate(verified_member)

        assert api_client.get(reverse("circle-child-list", args=[circle.id])).status_code == 403
        response = api_client.patch(
            reverse("child-birthdate", args=[sophia.id]), {"birthdate": "2020-01-01"}, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        sophia.refresh_from_db()
        assert sophia.birthdate == date(2023, 10, 16)

    def test_admins_of_another_circle_cannot_set(self, api_client, other_circle, outsider, sophia):
        outsider.email_verified = True
        outsider.save(update_fields=["email_verified"])
        api_client.force_authenticate(outsider)

        response = api_client.patch(
            reverse("child-birthdate", args=[sophia.id]), {"birthdate": "2020-01-01"}, format="json"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_sets_a_birthdate_and_the_album_picks_it_up(
        self, api_client, circle, verified_admin, django_capture_on_commit_callbacks
    ):
        enable(circle)
        child = ChildProfile.objects.create(circle=circle, display_name="Sophia")
        make_keep(circle, verified_admin, at(date(2024, 10, 16)), title="1st birthday")
        api_client.force_authenticate(verified_admin)

        with django_capture_on_commit_callbacks(execute=True):
            response = api_client.patch(
                reverse("child-birthdate", args=[child.id]),
                {"birthdate": "2023-10-16", "display_name": "Renamed"},
                format="json",
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["child"]["birthdate"] == "2023-10-16"
        child.refresh_from_db()
        assert (child.display_name, child.birthdate) == ("Sophia", date(2023, 10, 16))
        assert album_titles(Album.objects.get()) == ["1st birthday"]

    def test_setting_a_birthdate_while_turned_off_queues_nothing(
        self, api_client, circle, verified_admin, sophia, django_capture_on_commit_callbacks
    ):
        api_client.force_authenticate(verified_admin)

        with django_capture_on_commit_callbacks() as callbacks:
            response = api_client.patch(
                reverse("child-birthdate", args=[sophia.id]), {"birthdate": None}, format="json"
            )

        assert response.status_code == status.HTTP_200_OK
        assert callbacks == []
        sophia.refresh_from_db()
        assert sophia.birthdate is None

    def test_rejects_a_future_birthdate(self, api_client, circle, verified_admin, sophia):
        api_client.force_authenticate(verified_admin)

        response = api_client.patch(
            reverse("child-birthdate", args=[sophia.id]), {"birthdate": "2999-01-01"}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        sophia.refresh_from_db()
        assert sophia.birthdate == date(2023, 10, 16)
