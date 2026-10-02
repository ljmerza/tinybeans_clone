"""Tests for the album models."""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from mysite.albums.models import Album, AlbumKeep

from .helpers import make_album, make_keep


@pytest.mark.django_db
class TestAlbumKeep:
    def test_rejects_a_keep_from_another_circle(self, circle, other_circle, admin, outsider):
        album = make_album(circle, admin)
        foreign = make_keep(other_circle, outsider)

        with pytest.raises(ValidationError) as error:
            AlbumKeep.objects.create(album=album, keep=foreign, added_by=admin)

        assert "keep" in error.value.message_dict
        assert not AlbumKeep.objects.exists()

    def test_a_keep_is_in_an_album_once(self, circle, admin):
        keep = make_keep(circle, admin)
        album = make_album(circle, admin, keeps=[keep])

        with pytest.raises(IntegrityError), transaction.atomic():
            AlbumKeep.objects.create(album=album, keep=keep)

    def test_a_keep_can_be_in_many_albums(self, circle, admin):
        keep = make_keep(circle, admin)
        first = make_album(circle, admin, name="Summer", keeps=[keep])
        second = make_album(circle, admin, name="Beach", keeps=[keep])

        assert set(keep.albums.all()) == {first, second}

    def test_deleting_a_keep_takes_it_out_of_its_albums(self, circle, admin):
        keep = make_keep(circle, admin)
        album = make_album(circle, admin, keeps=[keep])
        album.cover_keep = keep
        album.save()

        keep.delete()

        album.refresh_from_db()
        assert album.album_keeps.count() == 0
        assert album.cover_keep is None

    def test_deleting_an_album_keeps_its_posts(self, circle, admin):
        keep = make_keep(circle, admin)
        album = make_album(circle, admin, keeps=[keep])

        album.delete()

        assert not AlbumKeep.objects.exists()
        keep.refresh_from_db()

    def test_deleting_the_creator_keeps_the_album(self, circle, admin, member):
        keep = make_keep(circle, admin)
        album = make_album(circle, member, keeps=[keep])
        AlbumKeep.objects.filter(album=album).update(added_by=member)

        member.delete()

        album.refresh_from_db()
        assert album.created_by is None
        assert album.album_keeps.get().added_by is None

    def test_deleting_the_circle_deletes_its_albums(self, circle, admin):
        make_album(circle, admin, keeps=[make_keep(circle, admin)])

        circle.delete()

        assert not Album.objects.exists()
        assert not AlbumKeep.objects.exists()
