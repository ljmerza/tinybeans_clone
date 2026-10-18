"""Tests for migration 0005, which links each circle's existing "Milestones" album."""

import importlib

import pytest
from django.apps import apps

from mysite.albums.models import MilestoneAlbum
from mysite.circles.models import Circle

from .helpers import make_album

link_migration = importlib.import_module("mysite.albums.migrations.0005_link_existing_milestones_album")


def run_link():
    link_migration.link_existing_milestones_albums(apps, None)


@pytest.mark.django_db
class TestLinkExistingMilestonesAlbum:
    def test_links_exactly_one_match_in_any_case(self, circle, admin):
        album = make_album(circle, admin, name="milestones")
        make_album(circle, admin, name="Beach trip")

        run_link()

        assert MilestoneAlbum.objects.get(circle=circle).album == album

    def test_skips_circles_with_none_or_several(self, circle, admin, other_circle, outsider):
        make_album(circle, admin, name="Beach trip")
        make_album(other_circle, outsider, name="Milestones")
        make_album(other_circle, outsider, name="MILESTONES")

        run_link()

        assert not MilestoneAlbum.objects.exists()

    def test_each_circle_on_its_own(self, circle, admin, other_circle, outsider):
        mine = make_album(circle, admin, name="Milestones")
        third = Circle.objects.create(name="Third", created_by=outsider)
        make_album(third, outsider, name="Milestones")
        make_album(third, outsider, name="Milestones")
        theirs = make_album(other_circle, outsider, name="Milestones")

        run_link()

        assert dict(MilestoneAlbum.objects.values_list("circle_id", "album_id")) == {
            circle.id: mine.id,
            other_circle.id: theirs.id,
        }

    def test_running_twice_is_harmless(self, circle, admin):
        album = make_album(circle, admin, name="Milestones")

        run_link()
        run_link()

        assert list(MilestoneAlbum.objects.values_list("album_id", flat=True)) == [album.id]

    def test_reverse_does_nothing(self):
        operation = link_migration.Migration.operations[0]

        assert operation.reverse_code is operation.noop
