"""Tests for the Milestones album and the milestone suggestion queue: the service, the review API, the setting."""

import logging
from contextlib import contextmanager
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as ModelValidationError
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework_simplejwt.authentication import JWTAuthentication

from mysite.albums import milestones
from mysite.albums.models import Album, AlbumKeep, MilestoneAlbum, MilestoneSuggestion
from mysite.albums.views_milestones import (
    MilestoneSuggestionApproveView,
    MilestoneSuggestionDismissView,
    MilestoneSuggestionListView,
)
from mysite.circles.models import Circle, CircleMembership
from mysite.users.models import UserRole

from .helpers import BASE_TIME, make_album, make_keep

User = get_user_model()
Status = MilestoneSuggestion.Status
Source = MilestoneSuggestion.Source


@contextmanager
def audit_records(caplog):
    """Capture ``mysite.audit`` records; the logger doesn't propagate outside tests."""
    audit_logger = logging.getLogger("mysite.audit")
    previous = audit_logger.propagate
    audit_logger.propagate = True
    try:
        with caplog.at_level(logging.INFO, logger="mysite.audit"):
            records = []
            yield records
            records.extend(record for record in caplog.records if record.name == "mysite.audit")
    finally:
        audit_logger.propagate = previous


def review_on(circle):
    Circle.objects.filter(pk=circle.pk).update(review_ai_milestones=True)
    circle.refresh_from_db()


def propose(circle, keep, *, source=Source.AI, label="First steps", reason="Walked across the room", **kwargs):
    return milestones.propose(circle_id=circle.id, keep=keep, source=source, label=label, reason=reason, **kwargs)


def suggestion_for(circle, keep, status=Status.PENDING, **kwargs):
    return MilestoneSuggestion.objects.create(
        circle=circle, keep=keep, status=status, source=kwargs.pop("source", Source.AI), **kwargs
    )


def milestones_album(circle):
    return MilestoneAlbum.objects.get(circle=circle).album


def in_milestones_album(circle, keep):
    return AlbumKeep.objects.filter(album__milestone_album__circle=circle, keep=keep).exists()


def list_url(circle_id):
    return reverse("circle-milestone-suggestion-list", args=[circle_id])


def approve_url(circle_id, suggestion_id):
    return reverse("circle-milestone-suggestion-approve", args=[circle_id, suggestion_id])


def dismiss_url(circle_id, suggestion_id):
    return reverse("circle-milestone-suggestion-dismiss", args=[circle_id, suggestion_id])


@pytest.fixture
def keep(circle, admin):
    return make_keep(circle, admin, title="First steps!")


@pytest.mark.django_db
class TestModel:
    def test_keep_must_be_in_the_same_circle(self, circle, other_circle, outsider):
        foreign = make_keep(other_circle, outsider)

        with pytest.raises(ModelValidationError):
            MilestoneSuggestion.objects.create(circle=circle, keep=foreign, status=Status.PENDING, source=Source.AI)

    def test_column_lengths_match_the_shared_contract(self):
        # SQLite doesn't enforce varchar lengths; Postgres does, so writers must stay within these.
        lengths = {field: MilestoneSuggestion._meta.get_field(field).max_length for field in ("label", "reason")}
        assert lengths == {"label": 80, "reason": 500}
        assert MilestoneSuggestion._meta.get_field("model_name").max_length == 160
        assert MilestoneSuggestion._meta.get_field("source_token_prefix").max_length == 12
        status_field = MilestoneSuggestion._meta.get_field("status")
        assert max(len(value) for value in Status.values) <= status_field.max_length
        source_field = MilestoneSuggestion._meta.get_field("source")
        assert max(len(value) for value in Source.values) <= source_field.max_length

    def test_review_is_off_by_default(self, circle):
        assert circle.review_ai_milestones is False

    def test_deleting_the_album_removes_the_link(self, circle, admin, keep):
        propose(circle, keep)
        milestones_album(circle).delete()

        assert not MilestoneAlbum.objects.filter(circle=circle).exists()
        assert MilestoneSuggestion.objects.get(keep=keep).status == Status.AUTO_ADDED


class TestMentionsBirthday:
    @pytest.mark.parametrize(
        "text",
        ["Happy birthday!", "1 month birthday", "Half birthday cake", "4 month bday", "Sophia turned 2", "b-day"],
    )
    def test_birthdays_of_any_kind(self, text):
        assert milestones.mentions_birthday(text) is True

    @pytest.mark.parametrize("text", ["First steps!", "6 months old today", "Turned 6 months", "Rolled over", "", None])
    def test_everything_else(self, text):
        assert milestones.mentions_birthday(text) is False


@pytest.mark.django_db
class TestPropose:
    def test_review_off_adds_the_post_to_a_new_milestones_album(self, circle, keep):
        result = propose(circle, keep, model_name="qwen3:14b")

        assert result.outcome == Status.AUTO_ADDED
        assert result.created is True
        suggestion = result.suggestion
        assert (suggestion.status, suggestion.source, suggestion.label) == (Status.AUTO_ADDED, Source.AI, "First steps")
        assert suggestion.model_name == "qwen3:14b"
        assert suggestion.decided_by is None
        album = milestones_album(circle)
        assert (album.name, album.created_by) == ("Milestones", None)
        entry = AlbumKeep.objects.get(album=album, keep=keep)
        assert entry.added_by is None

    def test_review_off_uses_the_linked_album(self, circle, admin, keep):
        album = make_album(circle, admin, name="Our firsts")
        MilestoneAlbum.objects.create(circle=circle, album=album)

        propose(circle, keep)

        assert list(album.album_keeps.values_list("keep_id", flat=True)) == [keep.id]
        assert Album.objects.count() == 1

    def test_review_off_links_the_only_existing_milestones_album(self, circle, admin, keep):
        album = make_album(circle, admin, name="milestones")

        propose(circle, keep)

        assert milestones_album(circle) == album
        assert list(album.album_keeps.values_list("keep_id", flat=True)) == [keep.id]
        assert Album.objects.count() == 1

    def test_several_milestones_albums_get_a_new_linked_one(self, circle, admin, other_circle, outsider, keep):
        first, second = make_album(circle, admin, name="Milestones"), make_album(circle, admin, name="MILESTONES")
        make_album(other_circle, outsider, name="Milestones")

        propose(circle, keep)

        album = milestones_album(circle)
        assert album not in (first, second)
        assert album.circle == circle
        assert in_milestones_album(circle, keep)

    def test_another_circles_milestones_album_is_not_linked(self, circle, other_circle, outsider, keep):
        foreign = make_album(other_circle, outsider, name="Milestones")

        propose(circle, keep)

        assert milestones_album(circle) != foreign
        assert not foreign.album_keeps.exists()

    def test_review_on_waits_for_an_admin(self, circle, keep):
        review_on(circle)

        result = propose(circle, keep, source=Source.AGENT, token_prefix="circ_abc1234")

        assert result.outcome == Status.PENDING
        assert result.created is True
        assert result.suggestion.source_token_prefix == "circ_abc1234"
        assert not in_milestones_album(circle, keep)
        assert not MilestoneAlbum.objects.exists()

    def test_a_post_from_another_circle_is_not_found(self, circle, other_circle, outsider):
        foreign = make_keep(other_circle, outsider)

        with pytest.raises(NotFound):
            propose(circle, foreign)
        assert not MilestoneSuggestion.objects.exists()

    @pytest.mark.parametrize(
        ("title", "description"),
        [("Happy 1st birthday!", ""), ("Cake", "her 1 month birthday"), ("Half birthday", "")],
    )
    def test_birthday_posts_are_refused(self, circle, admin, title, description):
        post = make_keep(circle, admin, title=title)
        post.description = description
        post.save(update_fields=["description"])

        result = propose(circle, post)

        assert result == milestones.ProposeResult(milestones.BIRTHDAY)
        assert not MilestoneSuggestion.objects.exists()

    def test_a_months_old_post_is_accepted(self, circle, admin):
        post = make_keep(circle, admin, title="6 months old and sitting up")

        assert propose(circle, post).outcome == Status.AUTO_ADDED

    def test_a_post_already_in_the_album_is_refused(self, circle, admin, keep):
        album = make_album(circle, admin, name="Milestones", keeps=[keep])
        MilestoneAlbum.objects.create(circle=circle, album=album)

        result = propose(circle, keep)

        assert result.outcome == milestones.IN_ALBUM
        assert not MilestoneSuggestion.objects.exists()

    def test_proposing_again_changes_nothing(self, circle, keep):
        review_on(circle)
        first = propose(circle, keep)

        again = propose(circle, keep, source=Source.AGENT, label="Other", reason="Other")

        assert (again.outcome, again.created) == (Status.PENDING, False)
        assert again.suggestion.pk == first.suggestion.pk
        assert MilestoneSuggestion.objects.get().label == "First steps"

    @pytest.mark.parametrize("review", [True, False])
    def test_an_api_token_overrules_the_ais_no(self, circle, keep, review):
        if review:
            review_on(circle)
        suggestion_for(circle, keep, status=Status.NOT_MILESTONE, model_name="qwen3:14b")

        result = propose(circle, keep, source=Source.AGENT, token_prefix="circ_abc1234")

        expected = Status.PENDING if review else Status.AUTO_ADDED
        assert (result.outcome, result.created) == (expected, True)
        suggestion = MilestoneSuggestion.objects.get()
        assert (suggestion.status, suggestion.source) == (expected, Source.AGENT)
        assert (suggestion.reason, suggestion.model_name) == ("Walked across the room", "")
        assert in_milestones_album(circle, keep) is not review

    def test_the_ai_does_not_overrule_itself(self, circle, keep):
        suggestion_for(circle, keep, status=Status.NOT_MILESTONE)

        result = propose(circle, keep)

        assert (result.outcome, result.created) == (Status.NOT_MILESTONE, False)
        assert not in_milestones_album(circle, keep)

    @pytest.mark.parametrize("decided", [Status.DISMISSED, Status.APPROVED])
    def test_decided_rows_are_never_reopened(self, circle, keep, decided):
        suggestion_for(circle, keep, status=decided)

        result = propose(circle, keep, source=Source.AGENT)

        assert (result.outcome, result.created) == (decided, False)
        assert MilestoneSuggestion.objects.get().status == decided

    def test_a_post_an_admin_took_out_is_not_put_back(self, circle, keep):
        propose(circle, keep)
        AlbumKeep.objects.filter(keep=keep).delete()

        result = propose(circle, keep, source=Source.AGENT)

        assert (result.outcome, result.created) == (Status.AUTO_ADDED, False)
        assert not in_milestones_album(circle, keep)

    @override_settings(MILESTONE_MAX_PENDING=2)
    def test_pending_cap(self, circle, admin):
        review_on(circle)
        posts = [make_keep(circle, admin, title=f"Post {n}") for n in range(3)]
        propose(circle, posts[0])
        propose(circle, posts[1])

        result = propose(circle, posts[2])

        assert result.outcome == milestones.PENDING_CAP
        assert not MilestoneSuggestion.objects.filter(keep=posts[2]).exists()

    @override_settings(MILESTONE_MAX_PENDING=1)
    def test_pending_rows_already_in_the_album_do_not_count(self, circle, admin):
        review_on(circle)
        first, second = make_keep(circle, admin, title="One"), make_keep(circle, admin, title="Two")
        propose(circle, first)
        # An admin adds the pending post to the album by hand.
        album = make_album(circle, admin, name="Milestones", keeps=[first])
        MilestoneAlbum.objects.create(circle=circle, album=album)

        assert propose(circle, second).outcome == Status.PENDING

    @override_settings(MILESTONE_MAX_PENDING=1)
    def test_the_cap_does_not_stop_picks_with_review_off(self, circle, admin):
        first, second = make_keep(circle, admin, title="One"), make_keep(circle, admin, title="Two")
        suggestion_for(circle, first, status=Status.PENDING)

        assert propose(circle, second).outcome == Status.AUTO_ADDED

    def test_overlong_text_is_cut_to_the_column_lengths(self, circle, keep):
        result = propose(circle, keep, label="L" * 100, reason="R" * 600, model_name="M" * 200)

        suggestion = MilestoneSuggestion.objects.get(pk=result.suggestion.pk)
        assert (len(suggestion.label), len(suggestion.reason), len(suggestion.model_name)) == (80, 500, 160)

    def test_audit_logged_without_the_text(self, circle, keep, caplog):
        with audit_records(caplog) as records:
            propose(circle, keep, source=Source.AGENT, token_prefix="circ_abc1234", reason="secret-ish reason")

        assert records, "expected an audit record"
        record = records[-1]
        assert record.extra["action"] == "milestone_suggestion.propose"
        assert record.extra["actor_type"] == "agent"
        assert record.extra["actor_id"] == "circ_abc1234"
        assert record.extra["metadata"]["status"] == Status.AUTO_ADDED
        assert "secret-ish reason" not in str(record.extra)

    def test_refusals_are_not_logged(self, circle, admin, caplog):
        post = make_keep(circle, admin, title="Happy birthday")

        with audit_records(caplog) as records:
            propose(circle, post)

        assert records == []


@pytest.mark.django_db
class TestApproveAndDismiss:
    def test_approve_makes_the_album_and_adds_the_post(self, circle, admin, keep):
        suggestion = suggestion_for(circle, keep)

        suggestion, album = milestones.approve(suggestion, admin)

        assert suggestion.status == Status.APPROVED
        assert suggestion.decided_by == admin
        assert suggestion.decided_at is not None
        assert album == milestones_album(circle)
        assert (album.name, album.created_by) == ("Milestones", admin)
        assert AlbumKeep.objects.get(album=album, keep=keep).added_by == admin

    def test_approve_twice_is_a_no_op(self, circle, admin, member, keep):
        suggestion = suggestion_for(circle, keep)
        milestones.approve(suggestion, admin)

        suggestion, album = milestones.approve(suggestion, member)

        assert suggestion.decided_by == admin
        assert album.album_keeps.count() == 1

    def test_approving_a_dismissed_suggestion_undoes_the_dismiss(self, circle, admin, keep):
        suggestion = suggestion_for(circle, keep)
        milestones.dismiss(suggestion, admin)

        suggestion, _ = milestones.approve(suggestion, admin)

        assert suggestion.status == Status.APPROVED
        assert in_milestones_album(circle, keep)

    def test_approve_when_the_post_was_added_by_hand(self, circle, admin, keep):
        album = make_album(circle, admin, name="Milestones", keeps=[keep])
        MilestoneAlbum.objects.create(circle=circle, album=album)
        suggestion = suggestion_for(circle, keep)

        suggestion, approved_into = milestones.approve(suggestion, admin)

        assert approved_into == album
        assert album.album_keeps.count() == 1

    @pytest.mark.parametrize("current", [Status.AUTO_ADDED, Status.NOT_MILESTONE])
    def test_only_pending_or_dismissed_can_be_approved(self, circle, admin, keep, current):
        suggestion = suggestion_for(circle, keep, status=current)

        with pytest.raises(ValidationError):
            milestones.approve(suggestion, admin)
        assert not in_milestones_album(circle, keep)

    def test_dismiss_clears_the_reason(self, circle, admin, keep):
        suggestion = suggestion_for(circle, keep, reason="Looks like a first")

        suggestion = milestones.dismiss(suggestion, admin)

        suggestion.refresh_from_db()
        assert (suggestion.status, suggestion.reason, suggestion.decided_by) == (Status.DISMISSED, "", admin)
        assert not in_milestones_album(circle, keep)

    def test_dismiss_twice_is_a_no_op(self, circle, admin, member, keep):
        suggestion = suggestion_for(circle, keep)
        milestones.dismiss(suggestion, admin)

        assert milestones.dismiss(suggestion, member).decided_by == admin

    @pytest.mark.parametrize("current", [Status.APPROVED, Status.AUTO_ADDED, Status.NOT_MILESTONE])
    def test_only_pending_can_be_dismissed(self, circle, admin, keep, current):
        suggestion = suggestion_for(circle, keep, status=current)

        with pytest.raises(ValidationError):
            milestones.dismiss(suggestion, admin)
        assert MilestoneSuggestion.objects.get().status == current

    def test_decisions_are_audit_logged(self, circle, admin, keep, caplog):
        other = make_keep(circle, admin, title="Rolled over")
        approved, dismissed = suggestion_for(circle, keep), suggestion_for(circle, other)

        with audit_records(caplog) as records:
            milestones.approve(approved, admin)
            milestones.dismiss(dismissed, admin)
            # No-ops log nothing.
            milestones.approve(approved, admin)
            milestones.dismiss(dismissed, admin)

        assert [record.extra["action"] for record in records] == [
            "milestone_suggestion.approve",
            "milestone_suggestion.dismiss",
        ]
        assert all(record.extra["actor_id"] == str(admin.pk) for record in records)


@pytest.mark.django_db
class TestReviewApi:
    def test_requires_authentication(self, api_client, circle, keep):
        suggestion = suggestion_for(circle, keep)

        assert api_client.get(list_url(circle.id)).status_code == status.HTTP_401_UNAUTHORIZED
        assert api_client.post(approve_url(circle.id, suggestion.id)).status_code == status.HTTP_401_UNAUTHORIZED
        assert api_client.post(dismiss_url(circle.id, suggestion.id)).status_code == status.HTTP_401_UNAUTHORIZED

    def test_jwt_only(self):
        for view in (MilestoneSuggestionListView, MilestoneSuggestionApproveView, MilestoneSuggestionDismissView):
            assert view.authentication_classes == [JWTAuthentication]

    def test_members_are_forbidden(self, api_client, circle, member, keep):
        suggestion = suggestion_for(circle, keep)
        api_client.force_authenticate(member)

        assert api_client.get(list_url(circle.id)).status_code == status.HTTP_403_FORBIDDEN
        assert api_client.post(approve_url(circle.id, suggestion.id)).status_code == status.HTTP_403_FORBIDDEN
        assert api_client.post(dismiss_url(circle.id, suggestion.id)).status_code == status.HTTP_403_FORBIDDEN
        assert MilestoneSuggestion.objects.get().status == Status.PENDING

    def test_outsiders_and_superusers_get_404(self, api_client, circle, outsider, keep):
        suggestion = suggestion_for(circle, keep)
        superuser = User.objects.create_superuser(email="root@example.com", password="rootpass123")

        for user in (outsider, superuser):
            api_client.force_authenticate(user)
            assert api_client.get(list_url(circle.id)).status_code == status.HTTP_404_NOT_FOUND
            assert api_client.post(approve_url(circle.id, suggestion.id)).status_code == status.HTTP_404_NOT_FOUND
            assert api_client.post(dismiss_url(circle.id, suggestion.id)).status_code == status.HTTP_404_NOT_FOUND
        assert MilestoneSuggestion.objects.get().status == Status.PENDING

    def test_another_circles_suggestion_is_not_found(self, api_client, circle, admin, other_circle, outsider):
        # The admin of both circles still can't reach circle B's row through circle A's URL.
        CircleMembership.objects.create(circle=other_circle, user=admin, role=UserRole.CIRCLE_ADMIN)
        foreign = suggestion_for(other_circle, make_keep(other_circle, outsider))
        api_client.force_authenticate(admin)

        assert api_client.post(approve_url(circle.id, foreign.id)).status_code == status.HTTP_404_NOT_FOUND
        assert api_client.post(dismiss_url(circle.id, foreign.id)).status_code == status.HTTP_404_NOT_FOUND
        assert api_client.get(list_url(circle.id)).data["count"] == 0
        assert MilestoneSuggestion.objects.get().status == Status.PENDING

    def test_lists_pending_newest_first_with_their_posts(self, api_client, circle, admin):
        older = suggestion_for(
            circle,
            make_keep(circle, admin, title="Older"),
            label="Rolling",
            reason="<img src=x onerror=alert(1)>",
            source=Source.AGENT,
            source_token_prefix="circ_abc1234",
        )
        newer = suggestion_for(circle, make_keep(circle, admin, title="Newer"), label="Crawling")
        MilestoneSuggestion.objects.filter(pk=older.pk).update(created_at=BASE_TIME)
        MilestoneSuggestion.objects.filter(pk=newer.pk).update(created_at=BASE_TIME + timedelta(days=1))
        suggestion_for(circle, make_keep(circle, admin, title="Done"), status=Status.DISMISSED)
        suggestion_for(circle, make_keep(circle, admin, title="Auto"), status=Status.AUTO_ADDED)
        api_client.force_authenticate(admin)

        response = api_client.get(list_url(circle.id))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2
        items = response.data["results"]
        assert [item["keep"]["title"] for item in items] == ["Newer", "Older"]
        assert set(items[1]) == {
            "id",
            "status",
            "source",
            "label",
            "reason",
            "model_name",
            "source_token_prefix",
            "created_at",
            "decided_at",
            "keep",
        }
        assert items[1]["id"] == str(older.id)
        assert items[1]["reason"] == "<img src=x onerror=alert(1)>"
        assert items[1]["source_token_prefix"] == "circ_abc1234"
        assert items[1]["keep"]["media"]

    def test_lists_dismissed(self, api_client, circle, admin):
        suggestion_for(circle, make_keep(circle, admin, title="Pending"))
        suggestion_for(circle, make_keep(circle, admin, title="Dismissed"), status=Status.DISMISSED)
        api_client.force_authenticate(admin)

        response = api_client.get(list_url(circle.id), {"status": "dismissed"})

        assert [item["keep"]["title"] for item in response.data["results"]] == ["Dismissed"]

    @pytest.mark.parametrize("value", ["approved", "auto_added", "not_milestone", "bogus"])
    def test_other_statuses_are_rejected(self, api_client, circle, admin, value):
        api_client.force_authenticate(admin)

        assert api_client.get(list_url(circle.id), {"status": value}).status_code == status.HTTP_400_BAD_REQUEST

    def test_leaves_out_posts_in_the_album_or_not_shown_in_the_feed(self, api_client, circle, admin):
        in_album = make_keep(circle, admin, title="In album")
        album = make_album(circle, admin, name="Milestones", keeps=[in_album])
        MilestoneAlbum.objects.create(circle=circle, album=album)
        suggestion_for(circle, in_album)
        suggestion_for(circle, make_keep(circle, admin, title="Processing", media=(("video", False),)))
        suggestion_for(circle, make_keep(circle, admin, title="Shown"))
        suggestion_for(circle, make_keep(circle, admin, title="Note", media=()))
        api_client.force_authenticate(admin)

        response = api_client.get(list_url(circle.id))

        assert sorted(item["keep"]["title"] for item in response.data["results"]) == ["Note", "Shown"]

    def test_paginates(self, api_client, circle, admin):
        for n in range(3):
            suggestion_for(circle, make_keep(circle, admin, title=f"Post {n}"))
        api_client.force_authenticate(admin)

        response = api_client.get(list_url(circle.id), {"limit": 2})

        assert response.data["count"] == 3
        assert len(response.data["results"]) == 2
        assert response.data["next"]

    def test_approve(self, api_client, circle, admin, keep):
        suggestion = suggestion_for(circle, keep)
        api_client.force_authenticate(admin)

        response = api_client.post(approve_url(circle.id, suggestion.id))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["suggestion"]["status"] == Status.APPROVED
        assert response.data["album_id"] == milestones_album(circle).pk
        assert in_milestones_album(circle, keep)

    def test_approving_an_auto_added_post_is_rejected(self, api_client, circle, admin, keep):
        suggestion = suggestion_for(circle, keep, status=Status.AUTO_ADDED)
        api_client.force_authenticate(admin)

        assert api_client.post(approve_url(circle.id, suggestion.id)).status_code == status.HTTP_400_BAD_REQUEST

    def test_dismiss(self, api_client, circle, admin, keep):
        suggestion = suggestion_for(circle, keep, reason="Looks like a first")
        api_client.force_authenticate(admin)

        response = api_client.post(dismiss_url(circle.id, suggestion.id))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["suggestion"]["status"] == Status.DISMISSED
        assert response.data["suggestion"]["reason"] == ""


@pytest.mark.django_db
class TestAiAddedTag:
    def keeps_url(self, album):
        return reverse("albums:album-keeps", args=[album.id])

    def test_admins_see_which_posts_ai_added(self, api_client, circle, admin, keep):
        propose(circle, keep)
        approved = make_keep(circle, admin, title="Approved", when=BASE_TIME.replace(day=2))
        milestones.approve(suggestion_for(circle, approved), admin)
        api_client.force_authenticate(admin)

        response = api_client.get(self.keeps_url(milestones_album(circle)))

        assert response.status_code == status.HTTP_200_OK
        assert {item["title"]: item["ai_added"] for item in response.data["results"]} == {
            "First steps!": True,
            "Approved": False,
        }

    def test_members_do_not_get_the_field(self, api_client, circle, member, keep):
        propose(circle, keep)
        api_client.force_authenticate(member)

        response = api_client.get(self.keeps_url(milestones_album(circle)))

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert "ai_added" not in response.data["results"][0]

    def test_only_in_the_milestones_album(self, api_client, circle, admin, keep):
        propose(circle, keep)
        other = make_album(circle, admin, keeps=[keep])
        api_client.force_authenticate(admin)

        response = api_client.get(self.keeps_url(other))

        assert response.data["results"][0]["ai_added"] is False


@pytest.mark.django_db
class TestMilestoneAlbumFlag:
    def test_albums_say_which_is_the_milestones_album(self, api_client, circle, member, admin, keep):
        propose(circle, keep)
        linked = milestones_album(circle)
        # Named like it, but not the linked one.
        other = make_album(circle, admin, name="Milestones")
        api_client.force_authenticate(member)

        listed = api_client.get(reverse("albums:album-list-create"))
        detail = api_client.get(reverse("albums:album-detail", args=[linked.id]))

        assert {item["id"]: item["is_milestone_album"] for item in listed.data["results"]} == {
            str(linked.id): True,
            str(other.id): False,
        }
        assert detail.data["is_milestone_album"] is True


@pytest.mark.django_db
class TestReviewSetting:
    @pytest.fixture
    def admin(self, admin):
        # Changing circle settings needs a verified email.
        admin.email_verified = True
        admin.save(update_fields=["email_verified"])
        return admin

    def test_admin_turns_it_on(self, api_client, circle, admin, caplog):
        api_client.force_authenticate(admin)

        with audit_records(caplog) as records:
            response = api_client.patch(
                reverse("circle-detail", args=[circle.id]), {"review_ai_milestones": True}, format="json"
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["circle"]["review_ai_milestones"] is True
        circle.refresh_from_db()
        assert circle.review_ai_milestones is True
        updates = [record for record in records if record.extra["action"] == "circle.ai_settings.update"]
        assert len(updates) == 1
        assert updates[0].extra["metadata"] == {"fields": ["review_ai_milestones"]}
        assert updates[0].extra["actor_id"] == str(admin.pk)

    def test_only_real_changes_are_logged(self, api_client, circle, admin, caplog):
        api_client.force_authenticate(admin)
        url = reverse("circle-detail", args=[circle.id])

        with audit_records(caplog) as records:
            unchanged = api_client.patch(url, {"review_ai_milestones": False}, format="json")
            renamed = api_client.patch(url, {"name": "Renamed"}, format="json")
            # A real change, so the test can't pass just because nothing was captured.
            changed = api_client.patch(url, {"review_ai_milestones": True}, format="json")

        statuses = {unchanged.status_code, renamed.status_code, changed.status_code}
        assert statuses == {status.HTTP_200_OK}
        updates = [record for record in records if record.extra["action"] == "circle.ai_settings.update"]
        assert len(updates) == 1

    def test_members_cannot_change_it(self, api_client, circle, member):
        api_client.force_authenticate(member)

        response = api_client.patch(
            reverse("circle-detail", args=[circle.id]), {"review_ai_milestones": True}, format="json"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        circle.refresh_from_db()
        assert circle.review_ai_milestones is False

    def test_superusers_who_are_not_circle_admins_cannot_change_it(self, api_client, circle, member):
        superuser = User.objects.create_superuser(email="root@example.com", password="rootpass123")
        User.objects.filter(pk=superuser.pk).update(email_verified=True)
        superuser.refresh_from_db()
        url = reverse("circle-detail", args=[circle.id])

        for user in (superuser, member):
            if user is member:
                # A superuser who is only a member of the circle is no admin either.
                User.objects.filter(pk=member.pk).update(is_superuser=True, is_staff=True)
                user.refresh_from_db()
            api_client.force_authenticate(user)
            response = api_client.patch(url, {"review_ai_milestones": True}, format="json")
            assert response.status_code == status.HTTP_403_FORBIDDEN

        circle.refresh_from_db()
        assert circle.review_ai_milestones is False

    def test_superusers_can_still_change_other_details(self, api_client, circle):
        superuser = User.objects.create_superuser(email="root@example.com", password="rootpass123")
        User.objects.filter(pk=superuser.pk).update(email_verified=True)
        superuser.refresh_from_db()
        api_client.force_authenticate(superuser)

        response = api_client.patch(reverse("circle-detail", args=[circle.id]), {"name": "Renamed"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        circle.refresh_from_db()
        assert circle.name == "Renamed"

    def test_shown_on_the_circle_settings_page(self, api_client, circle, admin):
        review_on(circle)
        api_client.force_authenticate(admin)

        response = api_client.get(reverse("circle-member-list", args=[circle.id]))

        assert response.data["data"]["circle"]["review_ai_milestones"] is True

    def test_switching_it_on_leaves_auto_added_posts_and_off_leaves_pending_rows(self, circle, admin):
        auto, pending = make_keep(circle, admin, title="Auto"), make_keep(circle, admin, title="Pending")
        propose(circle, auto)
        review_on(circle)
        propose(circle, pending)
        Circle.objects.filter(pk=circle.pk).update(review_ai_milestones=False)

        assert in_milestones_album(circle, auto)
        assert not in_milestones_album(circle, pending)
        assert MilestoneSuggestion.objects.get(keep=pending).status == Status.PENDING
