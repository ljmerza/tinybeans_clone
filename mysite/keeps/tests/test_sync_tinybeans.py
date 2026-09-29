"""Tests for the sync_tinybeans management command (API + storage mocked)."""

import shutil
import tempfile
from datetime import timedelta
from pathlib import Path
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from mysite.circles.models import Circle
from mysite.keeps.management.commands.sync_tinybeans import TinybeansApiError, TinybeansClient
from mysite.keeps.models import (
    Keep,
    KeepComment,
    KeepMedia,
    KeepReaction,
    TinybeansImportRecord,
    TinybeansSyncRun,
    TinybeansSyncStatus,
)
from mysite.keeps.tasks import sync_tinybeans_incremental
from mysite.users.models import ChildProfile, User

# 2023-06-15T12:00:00Z in ms
ENTRY_TS = 1686830400000
LOGIN_USER = {"id": 1, "emailAddress": "parent@example.com", "firstName": "Pat", "lastName": "Parent"}
JOURNAL = {
    "id": 900,
    "title": "Our Family",
    "children": [{"id": 55, "firstName": "Sam", "lastName": "Parent", "dob": "2020-02-01"}],
}
PHOTO_ENTRY = {
    "id": 111,
    "uuid": "abc-111",
    "type": "PHOTO",
    "timestamp": ENTRY_TS,
    "userId": 1,
    "caption": "First steps!",
    "blobs": {
        "p": "https://cdn.example.com/photos/full-p.jpg",
        "o2": "https://cdn.example.com/photos/full-o2.jpg",
        "t": "https://cdn.example.com/photos/t.jpg",
    },
    "comments": [
        {
            "id": 501,
            "details": "So cute!",
            "timestamp": ENTRY_TS + 60000,
            "user": {"id": 2, "emailAddress": "grandma@example.com", "firstName": "Grand", "lastName": "Ma"},
        },
    ],
    "emotions": [
        {"id": 601, "entryId": 111, "userId": 2, "type": {"label": "Love"}},
    ],
}
VIDEO_ENTRY = {
    "id": 113,
    "uuid": "abc-113",
    "type": "PHOTO",
    "attachmentType": "VIDEO",
    "attachmentUrl_mp4": "https://cdn.example.com/videos/clip-mp4.mp4",
    "timestamp": ENTRY_TS + 7200 * 1000,
    "userId": 1,
    "caption": "First steps on video",
    "blobs": {
        "p": "https://cdn.example.com/videos/poster-p.jpg",
        "o2": "https://cdn.example.com/videos/poster-o2.jpg",
    },
    "comments": [],
    "emotions": [],
}
NOTE_ENTRY = {
    "id": 112,
    "uuid": "abc-112",
    "type": "TEXT",
    "timestamp": ENTRY_TS + 3600 * 1000,
    "userId": 1,
    "caption": "Just a note",
    "blobs": {},
    "comments": [],
    "emotions": [],
}

AUNT_FOLLOWER = {
    "id": 70,
    "user": {"id": 3, "firstName": "Annie", "lastName": "Aunt", "emailAddress": "aunt@example.com"},
}


class FakeClient:
    """Stands in for TinybeansClient; serves the fixture journal/entries."""

    last_updated_since = None  # cutoff passed to iter_entries on the most recent run
    follower_detail_calls = []  # follower ids fetched via follower_user

    def __init__(self, entries=None, replies=None, followers=None):
        self.entries = entries if entries is not None else [PHOTO_ENTRY, NOTE_ENTRY]
        self.replies = replies or {}
        self.follower_list = followers or []

    def comment_replies(self, journal_id, entry_id, comment_id):
        return list(self.replies.get(comment_id, []))

    def login(self, username, password):
        return dict(LOGIN_USER)

    def set_token(self, token):
        pass

    def followings(self):
        return [{"journal": dict(JOURNAL)}]

    def followers(self, journal_id):
        # The list only carries names; emails come from follower_user.
        return [
            {"id": f["id"], "user": {k: v for k, v in f["user"].items() if k != "emailAddress"}}
            for f in self.follower_list
        ]

    def follower_user(self, journal_id, follower_id):
        FakeClient.follower_detail_calls.append(follower_id)
        return dict(next(f["user"] for f in self.follower_list if f["id"] == follower_id))

    def iter_entries(self, journal_id, start_ms=None, end_ms=None, updated_since_ms=None):
        FakeClient.last_updated_since = updated_since_ms
        yield from self.entries

    def download(self, url):
        return b"fake-image-bytes", "image/jpeg"


DELETED_KEYS = []


class FakeStorage:
    def save(self, file_content, filename, content_type=None):
        return f"keeps/test/{filename}"

    def delete(self, storage_key):
        DELETED_KEYS.append(storage_key)
        return True


class SyncTinybeansCommandTests(TestCase):
    def setUp(self):
        DELETED_KEYS.clear()
        FakeClient.last_updated_since = None
        FakeClient.follower_detail_calls = []
        self.thumbnail_calls = []

    def run_sync(self, *args, entries=None, replies=None, followers=None):
        calls = self.thumbnail_calls
        patches = [
            mock.patch(
                "mysite.keeps.management.commands.sync_tinybeans.TinybeansClient",
                lambda: FakeClient(entries=entries, replies=replies, followers=followers),
            ),
            mock.patch(
                "mysite.keeps.management.commands.sync_tinybeans.get_storage_backend",
                FakeStorage,
            ),
            mock.patch(
                "mysite.keeps.management.commands.sync_tinybeans.Command._generate_thumbnails",
                lambda self, media_id, source_key=None: calls.append((media_id, source_key)),
            ),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        call_command(
            "sync_tinybeans",
            "--email",
            "parent@example.com",
            "--password",
            "pw",
            *args,
        )

    def test_full_import_creates_everything(self):
        self.run_sync()

        circle = Circle.objects.get()
        self.assertEqual(circle.name, "Our Family")
        self.assertEqual(circle.created_by.email, "parent@example.com")
        self.assertEqual(ChildProfile.objects.get().display_name, "Sam Parent")

        self.assertEqual(Keep.objects.count(), 2)
        photo_keep = TinybeansImportRecord.objects.get(object_type="entry", tinybeans_id="111").keep
        self.assertEqual(photo_keep.keep_type, "media")
        self.assertEqual(photo_keep.description, "First steps!")
        media = KeepMedia.objects.get(keep=photo_keep)
        self.assertEqual(media.media_type, "photo")
        self.assertEqual(media.original_filename, "full-p.jpg")  # uncropped, not the o2 square
        self.assertEqual(self.thumbnail_calls, [(media.id, None)])

        comment = KeepComment.objects.get()
        self.assertEqual(comment.comment, "So cute!")
        self.assertEqual(comment.user.email, "grandma@example.com")

        reaction = KeepReaction.objects.get()
        self.assertEqual(reaction.reaction_type, "love")
        self.assertEqual(reaction.user.email, "grandma@example.com")

        # placeholder commenters cannot log in
        self.assertFalse(User.objects.get(email="grandma@example.com").is_active)

    def test_rerun_does_not_duplicate(self):
        self.run_sync()
        counts = (
            Circle.objects.count(),
            ChildProfile.objects.count(),
            Keep.objects.count(),
            KeepMedia.objects.count(),
            KeepComment.objects.count(),
            KeepReaction.objects.count(),
            User.objects.count(),
        )
        self.run_sync()
        self.assertEqual(
            counts,
            (
                Circle.objects.count(),
                ChildProfile.objects.count(),
                Keep.objects.count(),
                KeepMedia.objects.count(),
                KeepComment.objects.count(),
                KeepReaction.objects.count(),
                User.objects.count(),
            ),
        )

    def test_new_comment_on_synced_entry_is_added_on_rerun(self):
        self.run_sync()
        entry = {
            **PHOTO_ENTRY,
            "comments": PHOTO_ENTRY["comments"]
            + [
                {"id": 502, "details": "Wonderful", "user": {"id": 1, "emailAddress": "parent@example.com"}},
            ],
        }
        self.run_sync(entries=[entry, NOTE_ENTRY])
        self.assertEqual(KeepComment.objects.count(), 2)
        self.assertEqual(Keep.objects.count(), 2)  # entry itself not re-imported

    def test_date_range_filters_entries(self):
        # NOTE_ENTRY is one hour after ENTRY_TS (2023-06-15); a range covering
        # only 2023-06-15 keeps both, a range before it keeps none.
        self.run_sync("--start", "2023-01-01", "--end", "2023-03-01")
        self.assertEqual(Keep.objects.count(), 0)
        self.run_sync("--start", "2023-06-15", "--end", "2023-06-15")
        self.assertEqual(Keep.objects.count(), 2)

    def test_dry_run_writes_nothing(self):
        self.run_sync("--dry-run")
        self.assertEqual(Circle.objects.count(), 0)
        self.assertEqual(Keep.objects.count(), 0)
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(TinybeansImportRecord.objects.count(), 0)

    def test_memory_date_comes_from_day_fields_not_upload_time(self):
        # Uploaded 2023-06-15 12:00Z, but the user dated the memory 2023-06-10.
        backdated = dict(PHOTO_ENTRY, year=2023, month=6, day=10)
        self.run_sync(entries=[backdated])

        keep = Keep.objects.get()
        self.assertEqual(keep.date_of_memory.isoformat(), "2023-06-10T12:00:00+00:00")
        self.assertEqual(keep.created_at.isoformat(), "2023-06-15T12:00:00+00:00")

    def test_rerun_corrects_memory_date_of_existing_keep(self):
        # First import had no day fields (older importer used the upload time).
        self.run_sync(entries=[PHOTO_ENTRY])
        self.assertEqual(Keep.objects.get().date_of_memory.date().isoformat(), "2023-06-15")

        self.run_sync(entries=[dict(PHOTO_ENTRY, year=2023, month=6, day=10)])
        self.assertEqual(Keep.objects.count(), 1)
        self.assertEqual(Keep.objects.get().date_of_memory.date().isoformat(), "2023-06-10")

    def test_date_range_uses_memory_date(self):
        backdated = dict(PHOTO_ENTRY, year=2023, month=6, day=10)
        self.run_sync("--start", "2023-06-15", "--end", "2023-06-15", entries=[backdated])
        self.assertEqual(Keep.objects.count(), 0)
        self.run_sync("--start", "2023-06-10", "--end", "2023-06-10", entries=[backdated])
        self.assertEqual(Keep.objects.count(), 1)

    def test_video_entry_imports_mp4_and_poster(self):
        self.run_sync(entries=[VIDEO_ENTRY])

        media = KeepMedia.objects.get()
        self.assertEqual(media.media_type, "video")
        self.assertEqual(media.original_filename, "clip-mp4.mp4")
        self.assertEqual(self.thumbnail_calls, [(media.id, "keeps/test/poster-p.jpg")])

    def test_placeholder_poster_is_ignored(self):
        # Tinybeans serves a static "processing" card when a video has no poster.
        pending = dict(
            VIDEO_ENTRY,
            blobs={
                "p": "https://public.tinybeans.com/images/processingVideo-p.jpg",
                "o2": "https://public.tinybeans.com/images/processingVideo-o2.jpg",
            },
        )
        self.run_sync(entries=[pending])

        media = KeepMedia.objects.get()
        self.assertEqual(media.media_type, "video")
        self.assertEqual(self.thumbnail_calls, [])

        self.run_sync(entries=[pending])  # no retry storm on re-runs either
        self.assertEqual(self.thumbnail_calls, [])

    def test_rerun_adds_poster_for_video_without_renditions(self):
        self.run_sync(entries=[VIDEO_ENTRY])
        self.thumbnail_calls.clear()

        self.run_sync(entries=[VIDEO_ENTRY])

        media = KeepMedia.objects.get()
        self.assertEqual(self.thumbnail_calls, [(media.id, "keeps/test/poster-p.jpg")])

    def test_rerun_upgrades_square_crop_original_to_full_size(self):
        square_only = dict(PHOTO_ENTRY, blobs={"o2": "https://cdn.example.com/photos/full-o2.jpg"})
        self.run_sync(entries=[square_only])
        media = KeepMedia.objects.get()
        self.assertEqual(media.original_filename, "full-o2.jpg")
        self.thumbnail_calls.clear()

        self.run_sync(entries=[PHOTO_ENTRY])

        media.refresh_from_db()
        self.assertEqual(media.original_filename, "full-p.jpg")
        self.assertEqual(media.storage_key_original, "keeps/test/full-p.jpg")
        self.assertFalse(media.thumbnails_generated)
        self.assertIn("keeps/test/full-o2.jpg", DELETED_KEYS)
        self.assertEqual(self.thumbnail_calls, [(media.id, None)])
        self.assertEqual(KeepMedia.objects.count(), 1)

    def test_full_size_original_is_not_downloaded_again(self):
        self.run_sync(entries=[PHOTO_ENTRY])
        self.thumbnail_calls.clear()

        self.run_sync(entries=[PHOTO_ENTRY])

        self.assertEqual(self.thumbnail_calls, [])
        self.assertEqual(DELETED_KEYS, [])

    def test_deleted_comment_and_reaction_are_removed_on_rerun(self):
        self.run_sync(entries=[PHOTO_ENTRY])
        self.assertEqual(KeepComment.objects.count(), 1)
        self.assertEqual(KeepReaction.objects.count(), 1)

        gone = dict(
            PHOTO_ENTRY,
            comments=[dict(PHOTO_ENTRY["comments"][0], deleted=True)],
            emotions=[dict(PHOTO_ENTRY["emotions"][0], deleted=True)],
        )
        self.run_sync(entries=[gone])

        self.assertEqual(KeepComment.objects.count(), 0)
        self.assertEqual(KeepReaction.objects.count(), 0)
        self.assertFalse(TinybeansImportRecord.objects.filter(object_type="comment").exists())
        self.assertFalse(TinybeansImportRecord.objects.filter(object_type="emotion").exists())

    def test_entry_deleted_here_is_not_reimported(self):
        self.run_sync(entries=[PHOTO_ENTRY])
        keep = TinybeansImportRecord.objects.get(object_type="entry", tinybeans_id="111").keep
        media_count = KeepMedia.objects.count()
        keep.delete()

        new_comment = {"id": 502, "details": "Wonderful", "user": {"id": 1, "emailAddress": "parent@example.com"}}
        self.run_sync(entries=[dict(PHOTO_ENTRY, comments=PHOTO_ENTRY["comments"] + [new_comment])])

        self.assertEqual(Keep.objects.count(), 0)
        self.assertEqual(KeepMedia.objects.count(), 0)
        self.assertEqual(KeepComment.objects.count(), 0)
        self.assertEqual(KeepReaction.objects.count(), 0)
        self.assertGreater(media_count, 0)
        # The entry's row stays behind, without a keep, as the tombstone.
        record = TinybeansImportRecord.objects.get(object_type="entry", tinybeans_id="111")
        self.assertIsNone(record.keep_id)
        self.assertEqual(TinybeansSyncRun.objects.first().counts["entries_deleted_locally"], 1)

    def test_comment_and_reaction_deleted_here_are_not_reimported(self):
        self.run_sync(entries=[PHOTO_ENTRY])
        KeepComment.objects.get().delete()
        KeepReaction.objects.get().delete()  # unliked here

        self.run_sync(entries=[PHOTO_ENTRY])

        self.assertEqual(KeepComment.objects.count(), 0)
        self.assertEqual(KeepReaction.objects.count(), 0)
        # Their rows stay behind, without a local object, as tombstones.
        self.assertIsNone(TinybeansImportRecord.objects.get(object_type="comment").comment_id)
        self.assertIsNone(TinybeansImportRecord.objects.get(object_type="emotion").reaction_id)

    def test_new_reply_under_a_comment_deleted_here_is_not_imported(self):
        self.run_sync(entries=[PHOTO_ENTRY])
        KeepComment.objects.get().delete()

        threaded = dict(PHOTO_ENTRY, comments=[dict(PHOTO_ENTRY["comments"][0], repliesCount=1)])
        replies = {
            501: [
                {
                    "id": 502,
                    "parentId": 501,
                    "details": "Reply!",
                    "repliesCount": 0,
                    "timestamp": ENTRY_TS + 120000,
                    "user": dict(LOGIN_USER),
                }
            ],
        }
        self.run_sync(entries=[threaded], replies=replies)

        self.assertEqual(KeepComment.objects.count(), 0)
        self.assertFalse(TinybeansImportRecord.objects.filter(object_type="comment", tinybeans_id="502").exists())

    def test_deleted_comment_is_never_imported(self):
        entry = dict(PHOTO_ENTRY, comments=[dict(PHOTO_ENTRY["comments"][0], deleted=True)])
        self.run_sync(entries=[entry])
        self.assertEqual(KeepComment.objects.count(), 0)

    def test_replies_are_imported_as_comments(self):
        threaded = dict(PHOTO_ENTRY, comments=[dict(PHOTO_ENTRY["comments"][0], repliesCount=1)])
        replies = {
            501: [
                {
                    "id": 502,
                    "parentId": 501,
                    "details": "Reply!",
                    "repliesCount": 0,
                    "timestamp": ENTRY_TS + 120000,
                    "user": dict(LOGIN_USER),
                }
            ],
        }
        self.run_sync(entries=[threaded], replies=replies)

        self.assertEqual(KeepComment.objects.count(), 2)
        reply = TinybeansImportRecord.objects.get(object_type="comment", tinybeans_id="502").comment
        parent = TinybeansImportRecord.objects.get(object_type="comment", tinybeans_id="501").comment
        self.assertEqual(reply.comment, "Reply!")
        self.assertEqual(reply.user.email, "parent@example.com")
        self.assertEqual(reply.parent, parent)
        self.assertEqual(list(parent.replies.all()), [reply])

        # replies are keyed by their own id, so a rerun adds nothing
        self.run_sync(entries=[threaded], replies=replies)
        self.assertEqual(KeepComment.objects.count(), 2)

    def test_rerun_links_parent_of_previously_imported_reply(self):
        threaded = dict(PHOTO_ENTRY, comments=[dict(PHOTO_ENTRY["comments"][0], repliesCount=1)])
        replies = {
            501: [
                {
                    "id": 502,
                    "parentId": 501,
                    "details": "Reply!",
                    "repliesCount": 0,
                    "timestamp": ENTRY_TS + 120000,
                    "user": dict(LOGIN_USER),
                }
            ]
        }
        self.run_sync(entries=[threaded], replies=replies)
        KeepComment.objects.update(parent=None)  # as imported before threading existed

        self.run_sync(entries=[threaded], replies=replies)

        reply = TinybeansImportRecord.objects.get(object_type="comment", tinybeans_id="502").comment
        self.assertIsNotNone(reply.parent)
        self.assertEqual(reply.parent.comment, "So cute!")

    def test_child_tags_are_added_to_keep(self):
        tagged = dict(PHOTO_ENTRY, children=[{"id": 55, "firstName": "Sam", "lastName": "Parent"}])
        self.run_sync(entries=[tagged])
        keep = Keep.objects.get()
        self.assertEqual(keep.tags, "Sam")
        self.assertEqual([c.display_name for c in keep.children.all()], ["Sam Parent"])

        # rerun does not duplicate the tag or the link; child 56 is not a
        # journal child so it gets a tag but no link
        both = dict(tagged, children=tagged["children"] + [{"id": 56, "firstName": "Alex"}])
        self.run_sync(entries=[both])
        keep.refresh_from_db()
        self.assertEqual(keep.tags, "Sam, Alex")
        self.assertEqual(keep.children.count(), 1)

    def test_rerun_links_children_of_previously_imported_keep(self):
        tagged = dict(PHOTO_ENTRY, children=[{"id": 55, "firstName": "Sam", "lastName": "Parent"}])
        self.run_sync(entries=[tagged])
        Keep.objects.get().children.clear()  # as imported before the link existed

        self.run_sync(entries=[tagged])

        self.assertEqual(Keep.objects.get().children.count(), 1)

    def test_run_is_recorded(self):
        self.run_sync()

        run = TinybeansSyncRun.objects.get()
        self.assertEqual(run.status, TinybeansSyncStatus.SUCCESS)
        self.assertIsNotNone(run.finished_at)
        self.assertFalse(run.incremental)
        self.assertEqual(run.counts["entries"], 2)

    def test_dry_run_is_not_recorded(self):
        self.run_sync("--dry-run")
        self.assertEqual(TinybeansSyncRun.objects.count(), 0)

    def test_failed_run_is_recorded_as_failed(self):
        with mock.patch.object(FakeClient, "followings", return_value=[]), self.assertRaises(CommandError):
            self.run_sync()

        run = TinybeansSyncRun.objects.get()
        self.assertEqual(run.status, TinybeansSyncStatus.FAILED)
        self.assertIn("No Tinybeans journals", run.error)
        self.assertIsNotNone(run.finished_at)

    def test_since_last_run_uses_last_successful_start_minus_margin(self):
        self.run_sync()
        first = TinybeansSyncRun.objects.get()
        # a later failed run must not move the cutoff
        TinybeansSyncRun.objects.create(
            status=TinybeansSyncStatus.FAILED,
            started_at=first.started_at + timedelta(hours=2),
        )

        self.run_sync("--since-last-run")

        expected = int((first.started_at - timedelta(hours=1)).timestamp() * 1000)
        self.assertEqual(FakeClient.last_updated_since, expected)
        latest = TinybeansSyncRun.objects.order_by("-id").first()  # the fake FAILED row has a later started_at
        self.assertTrue(latest.incremental)
        self.assertEqual(latest.status, TinybeansSyncStatus.SUCCESS)

    def test_since_last_run_without_history_walks_everything(self):
        self.run_sync("--since-last-run")

        self.assertIsNone(FakeClient.last_updated_since)
        self.assertFalse(TinybeansSyncRun.objects.get().incremental)

    def test_deleted_entries_are_ignored(self):
        # Tinybeans leaves deleted entries in the feed with their media gone.
        deleted = dict(PHOTO_ENTRY, deleted=True)
        self.run_sync(entries=[deleted, NOTE_ENTRY])

        self.assertEqual(Keep.objects.count(), 1)
        self.assertFalse(TinybeansImportRecord.objects.filter(object_type="entry", tinybeans_id="111").exists())

    def test_followers_are_imported_with_real_email_and_names(self):
        # User 3 only ever reacts, so the entries alone would leave them a nameless placeholder.
        entry = dict(PHOTO_ENTRY, emotions=[{"id": 602, "entryId": 111, "userId": 3, "type": {"label": "Love"}}])
        self.run_sync(entries=[entry], followers=[AUNT_FOLLOWER])

        aunt = TinybeansImportRecord.objects.get(object_type="user", tinybeans_id="3").user
        self.assertEqual((aunt.email, aunt.first_name, aunt.last_name), ("aunt@example.com", "Annie", "Aunt"))
        self.assertEqual(KeepReaction.objects.get().user, aunt)
        self.assertTrue(aunt.circle_memberships.filter(circle=Circle.objects.get()).exists())

    def test_rerun_backfills_placeholder_user_from_followers(self):
        entry = dict(PHOTO_ENTRY, emotions=[{"id": 602, "entryId": 111, "userId": 3, "type": {"label": "Love"}}])
        self.run_sync(entries=[entry])
        placeholder = TinybeansImportRecord.objects.get(object_type="user", tinybeans_id="3").user
        self.assertTrue(placeholder.email.endswith("@tinybeans-import.invalid"))
        self.assertEqual(placeholder.first_name, "")

        self.run_sync(entries=[entry], followers=[AUNT_FOLLOWER])

        placeholder.refresh_from_db()
        self.assertEqual(
            (placeholder.email, placeholder.first_name, placeholder.last_name), ("aunt@example.com", "Annie", "Aunt")
        )
        self.assertEqual(TinybeansSyncRun.objects.latest("started_at").counts["users_updated"], 1)

    def test_backfill_never_overwrites_local_names_or_real_emails(self):
        self.run_sync(followers=[AUNT_FOLLOWER])
        aunt = User.objects.get(email="aunt@example.com")
        aunt.first_name = "Auntie"
        aunt.save()

        renamed = {"id": 70, "user": dict(AUNT_FOLLOWER["user"], firstName="Other", emailAddress="new@example.com")}
        self.run_sync(followers=[renamed])

        aunt.refresh_from_db()
        self.assertEqual((aunt.email, aunt.first_name), ("aunt@example.com", "Auntie"))

    def test_placeholder_is_not_merged_into_existing_account(self):
        entry = dict(PHOTO_ENTRY, emotions=[{"id": 602, "entryId": 111, "userId": 3, "type": {"label": "Love"}}])
        self.run_sync(entries=[entry])
        existing = User.objects.create_user(email="aunt@example.com", password="pw")

        self.run_sync(entries=[entry], followers=[AUNT_FOLLOWER])

        record = TinybeansImportRecord.objects.get(object_type="user", tinybeans_id="3")
        self.assertNotEqual(record.user, existing)
        self.assertTrue(record.user.email.endswith("@tinybeans-import.invalid"))
        self.assertEqual(record.user.first_name, "Annie")  # names are still filled in

    def test_new_follower_matching_existing_account_is_linked_and_named(self):
        existing = User.objects.create_user(email="aunt@example.com", password="pw")

        self.run_sync(followers=[AUNT_FOLLOWER])

        existing.refresh_from_db()
        self.assertEqual(TinybeansImportRecord.objects.get(object_type="user", tinybeans_id="3").user, existing)
        self.assertEqual((existing.first_name, existing.last_name), ("Annie", "Aunt"))

    def test_follower_detail_is_only_fetched_while_user_is_incomplete(self):
        self.run_sync(followers=[AUNT_FOLLOWER])
        self.assertEqual(FakeClient.follower_detail_calls, [70])

        self.run_sync(followers=[AUNT_FOLLOWER])
        self.assertEqual(FakeClient.follower_detail_calls, [70])

    def test_follower_listing_failure_does_not_stop_the_sync(self):
        with mock.patch.object(FakeClient, "followers", side_effect=TinybeansApiError("403")):
            self.run_sync()
        self.assertEqual(Keep.objects.count(), 2)


class TinybeansClientPagingTests(SimpleTestCase):
    """The entries endpoint pages by lastUpdatedTimestamp, not entry date."""

    DAY = 24 * 3600 * 1000
    NOW = ENTRY_TS + 400 * DAY

    def make_entries(self):
        # 7 entries, ids 1..7, dated one per day. Entry 1 is the oldest by date
        # but was updated most recently (a new comment), so it leads page 1.
        entries = []
        for i in range(1, 8):
            entries.append(
                {
                    "id": i,
                    "timestamp": ENTRY_TS + i * self.DAY,
                    "lastUpdatedTimestamp": ENTRY_TS + i * self.DAY + 3600 * 1000,
                }
            )
        entries[0]["lastUpdatedTimestamp"] = self.NOW - 1
        return entries

    def make_client(self, entries, page_size=3):
        client = TinybeansClient()
        client.calls = []
        by_updated = sorted(entries, key=lambda e: e["lastUpdatedTimestamp"], reverse=True)

        def entries_page(journal_id, last_ms):
            client.calls.append(last_ms)
            older = [e for e in by_updated if e["lastUpdatedTimestamp"] < last_ms]
            page = older[:page_size]
            return {"entries": page, "numEntriesRemaining": len(older) - len(page)}

        client.entries_page = entries_page
        return client

    def test_walks_every_entry_using_last_updated_cursor(self):
        entries = self.make_entries()
        client = self.make_client(entries)

        with mock.patch("mysite.keeps.management.commands.sync_tinybeans.time.time", return_value=self.NOW / 1000):
            got = list(client.iter_entries(900))

        self.assertEqual(sorted(e["id"] for e in got), list(range(1, 8)))
        # cursor after page 1 is the smallest lastUpdatedTimestamp on that page,
        # not the smallest entry date (which would have skipped ids 2..6)
        first_page = got[:3]
        self.assertEqual(client.calls[1], min(e["lastUpdatedTimestamp"] for e in first_page))
        self.assertEqual(len(client.calls), 3)

    def test_end_date_does_not_move_the_starting_cursor(self):
        entries = self.make_entries()
        client = self.make_client(entries)
        end_ms = ENTRY_TS + 2 * self.DAY  # would exclude entry 1 by lastUpdated

        with mock.patch("mysite.keeps.management.commands.sync_tinybeans.time.time", return_value=self.NOW / 1000):
            got = list(client.iter_entries(900, start_ms=None, end_ms=end_ms))

        self.assertIn(1, [e["id"] for e in got])
        self.assertGreaterEqual(client.calls[0], self.NOW)

    def test_updated_since_stops_paging_early(self):
        entries = self.make_entries()
        client = self.make_client(entries)
        # page 1 = ids 1, 7, 6 (by lastUpdated); its oldest update is day 6 + 1h
        since = ENTRY_TS + 6 * self.DAY + 2 * 3600 * 1000

        with mock.patch("mysite.keeps.management.commands.sync_tinybeans.time.time", return_value=self.NOW / 1000):
            got = list(client.iter_entries(900, updated_since_ms=since))

        self.assertEqual([e["id"] for e in got], [1, 7, 6])
        self.assertEqual(len(client.calls), 1)

    def test_start_date_stops_paging_early(self):
        entries = self.make_entries()
        client = self.make_client(entries)
        # page 1 is ids 1, 7, 6 (by lastUpdated); its oldest update is
        # entry 6 at day 6 + 1h, so a start just after that stops paging there.
        start_ms = ENTRY_TS + 6 * self.DAY + 2 * 3600 * 1000

        with mock.patch("mysite.keeps.management.commands.sync_tinybeans.time.time", return_value=self.NOW / 1000):
            got = list(client.iter_entries(900, start_ms=start_ms))

        self.assertEqual([e["id"] for e in got], [1, 7, 6])
        self.assertEqual(len(client.calls), 1)


class SyncTinybeansIncrementalTaskTests(TestCase):
    """The scheduled task fans out over every configured account, one cursor each."""

    # Explicit empties so an accounts file configured in the developer's own
    # environment cannot leak into the env-fallback tests.
    CREDS = {
        "TINYBEANS_ACCOUNTS_FILE": "",
        "TINYBEANS_EMAIL": "parent@example.com",
        "TINYBEANS_PASSWORD": "pw",
        "TINYBEANS_ACCESS_TOKEN": "",
        "TINYBEANS_OWNER": "",
    }

    def _accounts_file(self, body):
        path = Path(tempfile.mkdtemp()) / "accounts.yml"
        path.write_text(body)
        self.addCleanup(shutil.rmtree, path.parent)
        return {"TINYBEANS_ACCOUNTS_FILE": str(path)}

    def test_skips_without_credentials(self):
        with mock.patch.dict("os.environ", {}, clear=True), mock.patch("mysite.keeps.tasks.call_command") as call:
            self.assertEqual(sync_tinybeans_incremental(), 0)
        call.assert_not_called()

    def test_runs_incremental_sync_from_env_credentials(self):
        with mock.patch.dict("os.environ", self.CREDS), mock.patch("mysite.keeps.tasks.call_command") as call:
            self.assertEqual(sync_tinybeans_incremental(), 1)
        call.assert_called_once_with(
            "sync_tinybeans",
            since_last_run=True,
            account_key="parent@example.com",
            email="parent@example.com",
            password="pw",
            token=None,
            owner=None,
            journal=None,
        )

    def test_skips_while_the_same_account_is_in_progress(self):
        TinybeansSyncRun.objects.create(status=TinybeansSyncStatus.RUNNING, account_key="parent@example.com")
        with mock.patch.dict("os.environ", self.CREDS), mock.patch("mysite.keeps.tasks.call_command") as call:
            self.assertEqual(sync_tinybeans_incremental(), 0)
        call.assert_not_called()

    def test_another_accounts_run_does_not_block_this_one(self):
        TinybeansSyncRun.objects.create(status=TinybeansSyncStatus.RUNNING, account_key="someone-else@example.com")
        with mock.patch.dict("os.environ", self.CREDS), mock.patch("mysite.keeps.tasks.call_command") as call:
            self.assertEqual(sync_tinybeans_incremental(), 1)
        call.assert_called_once()

    def test_ignores_stale_running_rows(self):
        TinybeansSyncRun.objects.create(
            status=TinybeansSyncStatus.RUNNING,
            account_key="parent@example.com",
            started_at=timezone.now() - timedelta(hours=7),
        )
        with mock.patch.dict("os.environ", self.CREDS), mock.patch("mysite.keeps.tasks.call_command") as call:
            self.assertEqual(sync_tinybeans_incremental(), 1)
        call.assert_called_once()

    def test_syncs_every_account_in_the_file_with_its_own_families(self):
        env = self._accounts_file(
            """
            accounts:
              - email: one@example.com
                password: pw1
                families:
                  - id: 100
                    name: Merza
                  - 200
              - email: two@example.com
                password: pw2
                owner: local@example.com
            """
        )
        with mock.patch.dict("os.environ", env), mock.patch("mysite.keeps.tasks.call_command") as call:
            self.assertEqual(sync_tinybeans_incremental(), 2)

        self.assertEqual(
            [c.kwargs["account_key"] for c in call.call_args_list],
            ["one@example.com", "two@example.com"],
        )
        self.assertEqual(call.call_args_list[0].kwargs["journal"], ["100", "200"])
        self.assertIsNone(call.call_args_list[1].kwargs["journal"])
        self.assertEqual(call.call_args_list[1].kwargs["owner"], "local@example.com")

    def test_disabled_accounts_are_skipped(self):
        env = self._accounts_file(
            """
            accounts:
              - email: off@example.com
                password: pw
                enabled: false
              - email: on@example.com
                password: pw
            """
        )
        with mock.patch.dict("os.environ", env), mock.patch("mysite.keeps.tasks.call_command") as call:
            self.assertEqual(sync_tinybeans_incremental(), 1)
        self.assertEqual(call.call_args.kwargs["account_key"], "on@example.com")

    def test_one_failing_account_does_not_stop_the_others(self):
        env = self._accounts_file(
            """
            accounts:
              - email: broken@example.com
                password: pw
              - email: fine@example.com
                password: pw
            """
        )
        with (
            mock.patch.dict("os.environ", env),
            mock.patch("mysite.keeps.tasks.call_command", side_effect=[CommandError("login failed"), None]) as call,
        ):
            self.assertEqual(sync_tinybeans_incremental(), 1)
        self.assertEqual(call.call_count, 2)

    def test_unusable_accounts_file_is_skipped_without_raising(self):
        env = {"TINYBEANS_ACCOUNTS_FILE": "/nonexistent/accounts.yml"}
        with mock.patch.dict("os.environ", env), mock.patch("mysite.keeps.tasks.call_command") as call:
            self.assertEqual(sync_tinybeans_incremental(), 0)
        call.assert_not_called()
