"""Tests for Keep serializers."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory
from mysite.circles.models import Circle, CircleMembership
from mysite.keeps.models import Keep, KeepType, KeepMedia, Milestone, MilestoneType
from mysite.keeps.serializers import (
    KeepSerializer,
    KeepDetailSerializer,
    KeepCreateSerializer,
)

User = get_user_model()


@pytest.fixture
def user():
    """Create a test user."""
    return User.objects.create_user(
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def circle(user):
    """Create a test circle."""
    circle = Circle.objects.create(
        name='Test Family',
        created_by=user
    )
    # Membership for user is auto-created by the post_save signal on Circle
    return circle


@pytest.fixture
def keep(user, circle):
    """Create a test keep."""
    return Keep.objects.create(
        circle=circle,
        created_by=user,
        keep_type=KeepType.NOTE,
        title='Test Memory',
        description='A wonderful memory',
        tags='family,vacation,summer'
    )


@pytest.mark.django_db
class TestKeepSerializer:
    """Test KeepSerializer."""
    
    def test_serializer_contains_expected_fields(self, keep):
        """Test that serializer contains all expected fields."""
        serializer = KeepSerializer(instance=keep)
        data = serializer.data
        
        expected_fields = {
            'id', 'circle', 'circle_name', 'created_by', 'created_by_display_name',
            'keep_type', 'title', 'description', 'date_of_memory', 'created_at',
            'updated_at', 'is_public', 'tags', 'tag_list', 'media_count',
            'reaction_count', 'comment_count'
        }
        assert set(data.keys()) == expected_fields
        assert data['created_by_display_name'] == keep.created_by.display_name
    
    def test_tag_list_field(self, keep):
        """Test that tag_list field returns tags as a list."""
        serializer = KeepSerializer(instance=keep)
        data = serializer.data
        
        assert data['tag_list'] == ['family', 'vacation', 'summer']
    
    def test_tag_list_with_no_tags(self, user, circle):
        """Test tag_list returns empty list when no tags."""
        keep = Keep.objects.create(
            circle=circle,
            created_by=user,
            keep_type=KeepType.NOTE,
            title='No Tags',
            tags=''
        )
        serializer = KeepSerializer(instance=keep)
        data = serializer.data
        
        assert data['tag_list'] == []
    
    def test_media_count(self, keep):
        """Test media_count returns correct count."""
        # Initially no media
        serializer = KeepSerializer(instance=keep)
        assert serializer.data['media_count'] == 0
        
        # Add media
        KeepMedia.objects.create(
            keep=keep,
            media_type='photo',
            upload_order=1,
            storage_key_original='test.jpg',
            original_filename='test.jpg',
            content_type='image/jpeg'
        )
        
        serializer = KeepSerializer(instance=keep)
        assert serializer.data['media_count'] == 1
    
    def test_reaction_count(self, keep):
        """Test reaction_count returns correct count."""
        from mysite.keeps.models import KeepReaction
        
        serializer = KeepSerializer(instance=keep)
        assert serializer.data['reaction_count'] == 0
        
        # Add reaction
        KeepReaction.objects.create(
            keep=keep,
            user=keep.created_by,
            reaction_type='like'
        )
        
        serializer = KeepSerializer(instance=keep)
        assert serializer.data['reaction_count'] == 1
    
    def test_comment_count(self, keep):
        """Test comment_count returns correct count."""
        from mysite.keeps.models import KeepComment
        
        serializer = KeepSerializer(instance=keep)
        assert serializer.data['comment_count'] == 0
        
        # Add comment
        KeepComment.objects.create(
            keep=keep,
            user=keep.created_by,
            comment='Great memory!'
        )
        
        serializer = KeepSerializer(instance=keep)
        assert serializer.data['comment_count'] == 1


@pytest.mark.django_db
class TestKeepCreateSerializer:
    """Test KeepCreateSerializer."""
    
    def test_create_note_keep(self, user, circle):
        """Test creating a note-type keep."""
        data = {
            'circle': str(circle.id),
            'keep_type': KeepType.NOTE,
            'title': 'My Note',
            'description': 'A simple note',
            'tags': 'note,memory'
        }
        
        factory = APIRequestFactory()
        request = factory.post('/')
        request.user = user
        
        serializer = KeepCreateSerializer(data=data, context={'request': request})
        assert serializer.is_valid(), serializer.errors
        
        keep = serializer.save(created_by=user)
        assert keep.title == 'My Note'
        assert keep.keep_type == KeepType.NOTE
        assert keep.created_by == user
        assert keep.circle == circle
    
    def test_create_media_keep(self, user, circle):
        """Test creating a media-type keep."""
        data = {
            'circle': str(circle.id),
            'keep_type': KeepType.MEDIA,
            'title': 'Beach Day',
            'description': 'Fun at the beach',
        }
        
        factory = APIRequestFactory()
        request = factory.post('/')
        request.user = user
        
        serializer = KeepCreateSerializer(data=data, context={'request': request})
        assert serializer.is_valid(), serializer.errors
        
        keep = serializer.save(created_by=user)
        assert keep.keep_type == KeepType.MEDIA
    
    def test_validation_requires_circle(self, user):
        """Test that circle is required."""
        data = {
            'keep_type': KeepType.NOTE,
            'title': 'No Circle'
        }
        
        factory = APIRequestFactory()
        request = factory.post('/')
        request.user = user
        
        serializer = KeepCreateSerializer(data=data, context={'request': request})
        assert not serializer.is_valid()
        assert 'circle' in serializer.errors
    
    def test_validation_requires_valid_keep_type(self, user, circle):
        """Test that keep_type must be valid."""
        data = {
            'circle': str(circle.id),
            'keep_type': 'invalid_type',
            'title': 'Bad Type'
        }
        
        factory = APIRequestFactory()
        request = factory.post('/')
        request.user = user
        
        serializer = KeepCreateSerializer(data=data, context={'request': request})
        assert not serializer.is_valid()
        assert 'keep_type' in serializer.errors


@pytest.mark.django_db
class TestKeepDetailSerializer:
    """Test KeepDetailSerializer with related objects."""
    
    def test_includes_media_files(self, keep):
        """Test that detailed serializer includes media files."""
        # Add media
        media = KeepMedia.objects.create(
            keep=keep,
            media_type='photo',
            upload_order=1,
            storage_key_original='test.jpg',
            original_filename='test.jpg',
            content_type='image/jpeg'
        )
        
        serializer = KeepDetailSerializer(instance=keep)
        data = serializer.data
        
        assert 'media_files' in data
        assert len(data['media_files']) == 1
    
    def test_includes_milestone_data(self, user, circle):
        """Test that milestone data is included for milestone keeps."""
        keep = Keep.objects.create(
            circle=circle,
            created_by=user,
            keep_type=KeepType.MILESTONE,
            title='First Steps'
        )
        
        milestone = Milestone.objects.create(
            keep=keep,
            milestone_type=MilestoneType.FIRST_STEPS,
            age_at_milestone='12 months',
            is_first_time=True
        )
        
        serializer = KeepDetailSerializer(instance=keep)
        data = serializer.data
        
        assert 'milestone' in data
        assert data['milestone'] is not None
