"""Threaded comments: parent link, serializer exposure, and the backfill migration."""

from importlib import import_module

from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from mysite.circles.models import Circle, CircleMembership
from mysite.keeps.models import (
    Keep,
    KeepComment,
    KeepType,
    TinybeansImportRecord,
    TinybeansObjectType,
)
from mysite.keeps.serializers import KeepCommentSerializer
from mysite.users.models import UserRole

User = get_user_model()


class CommentThreadingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="thread@example.com", password="testpass123")
        self.circle = Circle.objects.create(name="Thread Family", created_by=self.user)
        self.keep = Keep.objects.create(circle=self.circle, created_by=self.user, keep_type=KeepType.NOTE)
        self.parent = KeepComment.objects.create(keep=self.keep, user=self.user, comment="Top level")
        self.reply = KeepComment.objects.create(
            keep=self.keep,
            user=self.user,
            comment="Reply",
            parent=self.parent,
        )

    def test_serializer_exposes_parent(self):
        self.assertEqual(KeepCommentSerializer(self.reply).data["parent"], self.parent.id)
        self.assertIsNone(KeepCommentSerializer(self.parent).data["parent"])

    def test_serializer_rejects_parent_on_another_keep(self):
        other_keep = Keep.objects.create(circle=self.circle, created_by=self.user, keep_type=KeepType.NOTE)
        other_parent = KeepComment.objects.create(keep=other_keep, user=self.user, comment="Elsewhere")

        serializer = KeepCommentSerializer(self.reply, data={"parent": other_parent.id}, partial=True)

        self.assertFalse(serializer.is_valid())
        self.assertIn("parent", serializer.errors)

    def test_reply_to_reply_joins_top_level_thread(self):
        request = RequestFactory().post("/")
        request.user = self.user
        CircleMembership.objects.get_or_create(user=self.user, circle=self.circle)

        serializer = KeepCommentSerializer(
            data={"keep": str(self.keep.id), "parent": self.reply.id, "comment": "@Thread me too"},
            context={"request": request},
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.save(user=self.user).parent, self.parent)

    def test_serializer_reports_can_delete_for_the_author(self):
        request = RequestFactory().get("/")
        request.user = self.user
        stranger = User.objects.create_user(email="stranger@example.com", password="testpass123")
        theirs = KeepComment.objects.create(keep=self.keep, user=stranger, comment="Not yours")
        CircleMembership.objects.filter(user=self.user, circle=self.circle).update(role=UserRole.CIRCLE_MEMBER)

        data = KeepCommentSerializer([self.parent, theirs], many=True, context={"request": request}).data

        self.assertEqual([c["can_delete"] for c in data], [True, False])

    def test_deleting_parent_removes_replies(self):
        self.parent.delete()
        self.assertFalse(KeepComment.objects.filter(pk=self.reply.pk).exists())

    def test_backfill_migration_links_replies_from_import_records(self):
        TinybeansImportRecord.objects.create(
            object_type=TinybeansObjectType.COMMENT,
            tinybeans_id="501",
            comment=self.parent,
            payload={"entryId": 111},
        )
        TinybeansImportRecord.objects.create(
            object_type=TinybeansObjectType.COMMENT,
            tinybeans_id="502",
            comment=self.reply,
            payload={"entryId": 111, "parentId": 501},
        )
        KeepComment.objects.filter(pk=self.reply.pk).update(parent=None)
        migration = import_module("mysite.keeps.migrations.0006_backfill_comment_parents")

        migration.backfill_comment_parents(apps, None)
        migration.backfill_comment_parents(apps, None)  # idempotent

        self.reply.refresh_from_db()
        self.assertEqual(self.reply.parent, self.parent)
        self.parent.refresh_from_db()
        self.assertIsNone(self.parent.parent)
