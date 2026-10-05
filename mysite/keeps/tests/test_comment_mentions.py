"""@mentions in comments: validation, storage, payloads, the mentionable list and notifications."""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from mysite.circles.models import Circle, CircleMembership
from mysite.keeps.models import Keep, KeepComment, KeepCommentMention, KeepType
from mysite.keeps.notifications import ActivityEvent, send_activity
from mysite.users.models import UserNotificationPreferences

User = get_user_model()

COMMENTS_URL = "/api/keeps/comments/"
FEED_URL = "/api/keeps/feed/"


def make_user(email, first_name, **extra):
    return User.objects.create_user(
        email=email, password="testpass123", first_name=first_name, email_verified=True, **extra
    )


def subjects():
    return {message.to[0]: message.subject for message in mail.outbox}


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def poster():
    return make_user("poster@example.com", "Pat")


@pytest.fixture
def grandma():
    return make_user("grandma@example.com", "Grandma")


@pytest.fixture
def uncle():
    return make_user("uncle@example.com", "Uncle")


@pytest.fixture
def outsider():
    return make_user("outsider@example.com", "Olive")


@pytest.fixture
def circle(poster, grandma, uncle):
    """The creator's membership comes from a signal; add the others."""
    circle = Circle.objects.create(name="Smith Family", created_by=poster)
    CircleMembership.objects.create(circle=circle, user=grandma)
    CircleMembership.objects.create(circle=circle, user=uncle)
    return circle


@pytest.fixture
def keep(circle, poster):
    return Keep.objects.create(circle=circle, created_by=poster, keep_type=KeepType.NOTE, description="Beach day")


@pytest.fixture
def post_comment(api_client, keep, django_capture_on_commit_callbacks):
    def post(author, text, mention_ids=None, parent=None):
        api_client.force_authenticate(user=author)
        payload = {"keep": str(keep.id), "comment": text}
        if mention_ids is not None:
            payload["mention_ids"] = mention_ids
        if parent is not None:
            payload["parent"] = parent.id
        with django_capture_on_commit_callbacks(execute=True):
            response = api_client.post(COMMENTS_URL, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED, response.data
        return response

    return post


@pytest.fixture
def edit_comment(api_client, django_capture_on_commit_callbacks):
    def edit(author, comment_id, payload):
        api_client.force_authenticate(user=author)
        with django_capture_on_commit_callbacks(execute=True):
            response = api_client.patch(f"{COMMENTS_URL}{comment_id}/", payload, format="json")
        assert response.status_code == status.HTTP_200_OK, response.data
        return response

    return edit


def mentioned_ids(comment_id):
    return list(KeepCommentMention.objects.filter(comment_id=comment_id).values_list("user_id", flat=True))


@pytest.mark.django_db
class TestStorageAndPayload:
    def test_stores_mentions_and_returns_them(self, post_comment, uncle, grandma):
        response = post_comment(uncle, "@Grandma look", mention_ids=[grandma.id])

        assert mentioned_ids(response.data["id"]) == [grandma.id]
        assert response.data["mentions"] == [{"id": grandma.id, "display_name": "Grandma"}]
        assert "mention_ids" not in response.data

    def test_without_mentions(self, post_comment, uncle):
        response = post_comment(uncle, "Lovely")

        assert response.data["mentions"] == []

    def test_drops_non_members_and_unknown_ids_but_keeps_the_comment(self, post_comment, uncle, grandma, outsider):
        response = post_comment(uncle, "@Grandma @Olive hi", mention_ids=[outsider.id, grandma.id, 999999])

        assert mentioned_ids(response.data["id"]) == [grandma.id]

    def test_repeated_ids_are_stored_once(self, post_comment, uncle, grandma):
        response = post_comment(uncle, "@Grandma @Grandma", mention_ids=[grandma.id, grandma.id])

        assert mentioned_ids(response.data["id"]) == [grandma.id]

    def test_self_mention_is_stored(self, post_comment, uncle):
        response = post_comment(uncle, "@Uncle note to self", mention_ids=[uncle.id])

        assert mentioned_ids(response.data["id"]) == [uncle.id]

    def test_rejects_non_integer_ids(self, api_client, keep, uncle):
        api_client.force_authenticate(user=uncle)

        response = api_client.post(
            COMMENTS_URL, {"keep": str(keep.id), "comment": "hi", "mention_ids": ["abc"]}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not KeepComment.objects.exists()

    def test_comment_list_includes_mentions(self, api_client, post_comment, keep, uncle, grandma):
        post_comment(uncle, "@Grandma look", mention_ids=[grandma.id])

        response = api_client.get(COMMENTS_URL, {"keep": str(keep.id)})

        assert response.data["results"][0]["mentions"] == [{"id": grandma.id, "display_name": "Grandma"}]

    def test_feed_preview_includes_mentions(self, api_client, post_comment, uncle, grandma):
        post_comment(uncle, "@Grandma look", mention_ids=[grandma.id])

        response = api_client.get(FEED_URL)

        comment = response.data["results"][0]["recent_comments"][0]
        assert comment["mentions"] == [{"id": grandma.id, "display_name": "Grandma"}]

    def test_feed_query_count_does_not_grow_with_mentions(self, api_client, circle, poster, grandma, uncle):
        api_client.force_authenticate(user=poster)
        first = Keep.objects.create(circle=circle, created_by=poster, keep_type=KeepType.NOTE, description="One")
        comment = KeepComment.objects.create(keep=first, user=uncle, comment="@Grandma hi")
        KeepCommentMention.objects.create(comment=comment, user=grandma)
        with CaptureQueriesContext(connection) as small:
            api_client.get(FEED_URL)

        for n in range(3):
            more = Keep.objects.create(
                circle=circle,
                created_by=poster,
                keep_type=KeepType.NOTE,
                description=f"More {n}",
                date_of_memory=timezone.now() - timedelta(days=n + 1),
            )
            comment = KeepComment.objects.create(keep=more, user=uncle, comment="@Grandma @Pat")
            KeepCommentMention.objects.create(comment=comment, user=grandma)
            KeepCommentMention.objects.create(comment=comment, user=poster)
        with CaptureQueriesContext(connection) as large:
            api_client.get(FEED_URL)

        assert len(large.captured_queries) == len(small.captured_queries)

    def test_edit_replaces_mentions_and_omitting_them_keeps_them(
        self, edit_comment, post_comment, uncle, grandma, poster
    ):
        comment_id = post_comment(uncle, "@Grandma hi", mention_ids=[grandma.id]).data["id"]

        edit_comment(uncle, comment_id, {"comment": "@Grandma hi!"})
        assert mentioned_ids(comment_id) == [grandma.id]

        response = edit_comment(uncle, comment_id, {"comment": "@Pat hi", "mention_ids": [poster.id]})
        assert mentioned_ids(comment_id) == [poster.id]
        assert response.data["mentions"] == [{"id": poster.id, "display_name": "Pat"}]


@pytest.mark.django_db
class TestMentionableMembers:
    def url(self, circle):
        return f"/api/keeps/circles/{circle.id}/mentionable/"

    def test_lists_the_other_members_in_name_order(self, api_client, circle, poster, grandma, uncle):
        api_client.force_authenticate(user=grandma)

        response = api_client.get(self.url(circle))

        assert response.status_code == status.HTTP_200_OK
        assert response.data == [
            {"id": poster.id, "display_name": "Pat"},
            {"id": uncle.id, "display_name": "Uncle"},
        ]

    def test_leaves_out_inactive_users(self, api_client, circle, grandma, uncle):
        uncle.is_active = False
        uncle.save()
        api_client.force_authenticate(user=grandma)

        response = api_client.get(self.url(circle))

        assert [member["display_name"] for member in response.data] == ["Pat"]

    def test_non_member_gets_404(self, api_client, circle, outsider):
        api_client.force_authenticate(user=outsider)

        response = api_client.get(self.url(circle))

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestMentionNotifications:
    def test_mention_emails_the_member_and_the_post_author_gets_the_comment_notice(self, post_comment, uncle, grandma):
        post_comment(uncle, "@Grandma look at this", mention_ids=[grandma.id])

        assert subjects() == {
            "grandma@example.com": "Uncle mentioned you in Smith Family",
            "poster@example.com": "Uncle commented on your post in Smith Family",
        }
        mention_email = next(message for message in mail.outbox if message.to == ["grandma@example.com"])
        assert "@Grandma look at this" in mention_email.body
        assert "/profile/notifications" in mention_email.body

    def test_mentioning_the_post_author_sends_one_notice(self, post_comment, uncle, poster):
        post_comment(uncle, "@Pat great shot", mention_ids=[poster.id])

        assert subjects() == {"poster@example.com": "Uncle mentioned you in Smith Family"}

    def test_reply_tag_is_a_mention_but_the_person_replied_to_gets_only_the_reply(
        self, post_comment, keep, grandma, uncle
    ):
        parent = KeepComment.objects.create(keep=keep, user=grandma, comment="So sweet")

        response = post_comment(uncle, "@Grandma agreed", mention_ids=[grandma.id], parent=parent)

        assert mentioned_ids(response.data["id"]) == [grandma.id]
        assert subjects() == {
            "grandma@example.com": "Uncle replied to you in Smith Family",
            "poster@example.com": "Uncle commented on your post in Smith Family",
        }

    def test_reply_that_mentions_someone_else_notifies_each_once(self, post_comment, keep, grandma, uncle, poster):
        parent = KeepComment.objects.create(keep=keep, user=grandma, comment="So sweet")

        post_comment(uncle, "@Grandma @Pat agreed", mention_ids=[grandma.id, poster.id], parent=parent)

        assert len(mail.outbox) == 2
        assert subjects() == {
            "grandma@example.com": "Uncle replied to you in Smith Family",
            "poster@example.com": "Uncle mentioned you in Smith Family",
        }

    def test_self_mention_notifies_no_one_but_the_post_author(self, post_comment, uncle):
        post_comment(uncle, "@Uncle remember this", mention_ids=[uncle.id])

        assert subjects() == {"poster@example.com": "Uncle commented on your post in Smith Family"}

    def test_post_author_mentioning_themselves_sends_nothing(self, post_comment, poster):
        post_comment(poster, "@Pat me", mention_ids=[poster.id])

        assert mail.outbox == []

    def test_non_member_mention_sends_nothing_to_them(self, post_comment, uncle, outsider):
        post_comment(uncle, "@Olive hi", mention_ids=[outsider.id])

        assert "outsider@example.com" not in subjects()

    def test_member_who_left_is_not_notified(self, keep, circle, grandma, uncle):
        comment = KeepComment.objects.create(keep=keep, user=uncle, comment="@Grandma hi")
        KeepCommentMention.objects.create(comment=comment, user=grandma)
        CircleMembership.objects.filter(circle=circle, user=grandma).delete()

        send_activity(ActivityEvent.COMMENT, str(comment.id))

        assert "grandma@example.com" not in subjects()

    def test_mentions_follow_the_replies_setting(self, post_comment, grandma, uncle):
        UserNotificationPreferences.objects.create(user=grandma, replies_email=False)

        post_comment(uncle, "@Grandma look", mention_ids=[grandma.id])

        assert "grandma@example.com" not in subjects()

    def test_circle_override_can_turn_mentions_back_on(self, post_comment, circle, grandma, uncle):
        UserNotificationPreferences.objects.create(user=grandma, replies_email=False)
        UserNotificationPreferences.objects.create(user=grandma, circle=circle, replies_email=True)

        post_comment(uncle, "@Grandma look", mention_ids=[grandma.id])

        assert subjects()["grandma@example.com"] == "Uncle mentioned you in Smith Family"

    def test_edit_notifies_only_newly_mentioned_members(self, post_comment, edit_comment, grandma, uncle, circle):
        aunt = make_user("aunt@example.com", "Aunt")
        CircleMembership.objects.create(circle=circle, user=aunt)
        comment_id = post_comment(uncle, "@Grandma hi", mention_ids=[grandma.id]).data["id"]
        mail.outbox.clear()

        edit_comment(uncle, comment_id, {"comment": "@Grandma hi!", "mention_ids": [grandma.id]})
        assert mail.outbox == []

        edit_comment(uncle, comment_id, {"comment": "@Grandma @Aunt hi", "mention_ids": [grandma.id, aunt.id]})
        assert subjects() == {"aunt@example.com": "Uncle mentioned you in Smith Family"}

    def test_edit_mentioning_the_post_author_does_not_notify_again(self, post_comment, edit_comment, uncle, poster):
        comment_id = post_comment(uncle, "Nice").data["id"]
        mail.outbox.clear()

        edit_comment(uncle, comment_id, {"comment": "@Pat nice", "mention_ids": [poster.id]})

        assert mail.outbox == []

    def test_edit_tagging_the_person_replied_to_does_not_notify_again(
        self, post_comment, edit_comment, keep, grandma, uncle
    ):
        parent = KeepComment.objects.create(keep=keep, user=grandma, comment="So sweet")
        comment_id = post_comment(uncle, "agreed", parent=parent).data["id"]
        mail.outbox.clear()

        edit_comment(uncle, comment_id, {"comment": "@Grandma agreed", "mention_ids": [grandma.id]})

        assert mail.outbox == []

    def test_rows_written_directly_do_not_notify(self, keep, grandma, uncle, django_capture_on_commit_callbacks):
        """The Tinybeans import writes rows through the ORM; imported history must stay quiet."""
        with django_capture_on_commit_callbacks(execute=True):
            comment = KeepComment.objects.create(keep=keep, user=uncle, comment="@Grandma imported")
            KeepCommentMention.objects.create(comment=comment, user=grandma)

        assert mail.outbox == []

    def test_deleted_mention_sends_nothing(self, keep, grandma, uncle):
        comment = KeepComment.objects.create(keep=keep, user=uncle, comment="@Grandma hi")
        mention = KeepCommentMention.objects.create(comment=comment, user=grandma)
        mention_id = str(mention.id)
        comment.delete()

        send_activity(ActivityEvent.MENTION, mention_id)

        assert mail.outbox == []
