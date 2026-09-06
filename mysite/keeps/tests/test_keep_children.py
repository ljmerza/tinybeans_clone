"""Keep <-> ChildProfile link: serializer exposure and the tag backfill migration."""
from importlib import import_module

from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import TestCase

from mysite.circles.models import Circle
from mysite.keeps.models import Keep, KeepType
from mysite.keeps.serializers import KeepSerializer
from mysite.users.models.child_profile import ChildProfile

User = get_user_model()


class KeepChildrenTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='kids@example.com', password='testpass123')
        self.circle = Circle.objects.create(name='Kids Family', created_by=self.user)
        self.sophia = ChildProfile.objects.create(circle=self.circle, display_name='Sophia M')
        self.aubrey = ChildProfile.objects.create(circle=self.circle, display_name='Aubrey Merza')

    def test_serializer_lists_children(self):
        keep = Keep.objects.create(circle=self.circle, created_by=self.user, keep_type=KeepType.NOTE)
        keep.children.add(self.sophia)

        data = KeepSerializer(keep).data

        self.assertEqual(data['children'], [{'id': str(self.sophia.id), 'display_name': 'Sophia M'}])

    def test_backfill_migration_links_children_from_tags(self):
        tagged = Keep.objects.create(
            circle=self.circle, created_by=self.user, keep_type=KeepType.NOTE, tags='sophia, Aubrey, beach',
        )
        untagged = Keep.objects.create(circle=self.circle, created_by=self.user, keep_type=KeepType.NOTE)
        other_circle = Circle.objects.create(name='Other', created_by=self.user)
        elsewhere = Keep.objects.create(
            circle=other_circle, created_by=self.user, keep_type=KeepType.NOTE, tags='Sophia',
        )
        migration = import_module('mysite.keeps.migrations.0008_backfill_keep_children')

        migration.backfill_keep_children(apps, None)
        migration.backfill_keep_children(apps, None)  # idempotent

        self.assertEqual(set(tagged.children.all()), {self.sophia, self.aubrey})
        self.assertEqual(untagged.children.count(), 0)
        self.assertEqual(elsewhere.children.count(), 0)  # no matching child in that circle
