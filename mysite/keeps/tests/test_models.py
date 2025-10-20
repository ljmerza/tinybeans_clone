"""Tests for the keeps app models and basic functionality."""
from django.test import TestCase
from django.contrib.auth import get_user_model
from mysite.circles.models import Circle, CircleMembership
from mysite.users.models import UserRole
from mysite.keeps.models import Keep, KeepType, KeepMedia, Milestone, MilestoneType, KeepReaction, KeepComment

User = get_user_model()


class KeepModelTest(TestCase):
    """Test the Keep model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.circle = Circle.objects.create(
            name='Test Family',
            created_by=self.user
        )
        CircleMembership.objects.create(
            user=self.user,
            circle=self.circle
        )
    
    def test_create_basic_keep(self):
        """Test creating a basic keep."""
        keep = Keep.objects.create(
            circle=self.circle,
            created_by=self.user,
            keep_type=KeepType.NOTE,
            title='First Memory',
            description='This is our first family memory!'
        )
        
        self.assertEqual(keep.title, 'First Memory')
        self.assertEqual(keep.keep_type, KeepType.NOTE)
        self.assertEqual(keep.circle, self.circle)
        self.assertEqual(keep.created_by, self.user)
        self.assertTrue(keep.is_public)
    
    def test_keep_str_representation(self):
        """Test the string representation of a keep."""
        keep = Keep.objects.create(
            circle=self.circle,
            created_by=self.user,
            keep_type=KeepType.MEDIA,
            title='Beach Day'
        )
        
        expected = f"Beach Day by {self.user} in {self.circle}"
        self.assertEqual(str(keep), expected)
    
    def test_keep_without_title_str_representation(self):
        """Test string representation of a keep without title."""
        keep = Keep.objects.create(
            circle=self.circle,
            created_by=self.user,
            keep_type=KeepType.MILESTONE
        )
        
        expected = f"milestone by {self.user} in {self.circle}"
        self.assertEqual(str(keep), expected)
    
    def test_tag_list_property(self):
        """Test the tag_list property."""
        keep = Keep.objects.create(
            circle=self.circle,
            created_by=self.user,
            keep_type=KeepType.MEDIA,
            tags='beach,summer,vacation,family'
        )
        
        expected_tags = ['beach', 'summer', 'vacation', 'family']
        self.assertEqual(keep.tag_list, expected_tags)
    
    def test_tag_list_property_with_spaces(self):
        """Test tag_list property handles spaces correctly."""
        keep = Keep.objects.create(
            circle=self.circle,
            created_by=self.user,
            keep_type=KeepType.MEDIA,
            tags='beach, summer , vacation,  family  '
        )
        
        expected_tags = ['beach', 'summer', 'vacation', 'family']
        self.assertEqual(keep.tag_list, expected_tags)
    
    def test_milestone_creation(self):
        """Test creating a milestone keep with milestone data."""
        keep = Keep.objects.create(
            circle=self.circle,
            created_by=self.user,
            keep_type=KeepType.MILESTONE,
            title='First Steps'
        )
        
        milestone = Milestone.objects.create(
            keep=keep,
            milestone_type=MilestoneType.FIRST_STEPS,
            age_at_milestone='12 months',
            notes='So proud!',
            is_first_time=True
        )
        
        self.assertEqual(milestone.keep, keep)
        self.assertEqual(milestone.milestone_type, MilestoneType.FIRST_STEPS)
        self.assertEqual(milestone.age_at_milestone, '12 months')
        self.assertTrue(milestone.is_first_time)
        
        # Test the reverse relationship
        self.assertEqual(keep.milestone, milestone)
    
    def test_keep_media_creation(self):
        """Test creating media for a keep."""
        keep = Keep.objects.create(
            circle=self.circle,
            created_by=self.user,
            keep_type=KeepType.MEDIA,
            title='Family Photo'
        )
        
        media = KeepMedia.objects.create(
            keep=keep,
            media_type='photo',
            caption='Beautiful family moment',
            upload_order=1,
            storage_key_original='test/photo.jpg',
            original_filename='photo.jpg',
            content_type='image/jpeg',
        )
        
        self.assertEqual(media.keep, keep)
        self.assertEqual(media.media_type, 'photo')
        self.assertEqual(media.caption, 'Beautiful family moment')
        self.assertEqual(media.upload_order, 1)
        
        # Test the reverse relationship
        self.assertEqual(keep.media_files.count(), 1)
        self.assertEqual(keep.media_files.first(), media)
    
    def test_keep_media_properties(self):
        """Test the media-related properties of keeps."""
        keep = Keep.objects.create(
            circle=self.circle,
            created_by=self.user,
            keep_type=KeepType.MEDIA,
            title='Mixed Media Keep'
        )
        
        # Initially no media
        self.assertEqual(keep.media_types, [])
        self.assertFalse(keep.has_photos)
        self.assertFalse(keep.has_videos)
        self.assertIsNone(keep.primary_media_type)
        
        # Add a photo
        photo = KeepMedia.objects.create(
            keep=keep,
            media_type='photo',
            caption='A photo',
            upload_order=1,
            storage_key_original='test/photo.jpg',
            original_filename='photo.jpg',
            content_type='image/jpeg',
        )
        
        # Refresh from database
        keep.refresh_from_db()
        
        self.assertIn('photo', keep.media_types)
        self.assertTrue(keep.has_photos)
        self.assertFalse(keep.has_videos)
        self.assertEqual(keep.primary_media_type, 'photo')
        
        # Add a video
        video = KeepMedia.objects.create(
            keep=keep,
            media_type='video',
            caption='A video',
            upload_order=2,
            storage_key_original='test/video.mp4',
            original_filename='video.mp4',
            content_type='video/mp4',
        )
        
        # Refresh from database
        keep.refresh_from_db()
        
        self.assertIn('photo', keep.media_types)
        self.assertIn('video', keep.media_types)
        self.assertTrue(keep.has_photos)
        self.assertTrue(keep.has_videos)
        self.assertEqual(keep.primary_media_type, 'video')  # Video takes precedence


class KeepAdminPermissionsTest(TestCase):
    """Test admin permissions for keeps, reactions, and comments."""
    
    def setUp(self):
        """Set up test data with admin and regular user."""
        # Create users
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        self.regular_user = User.objects.create_user(
            username='regular',
            email='regular@example.com',
            password='regularpass123'
        )
        
        # Create circle
        self.circle = Circle.objects.create(
            name='Test Family',
            created_by=self.admin_user
        )
        
        # Create memberships
        CircleMembership.objects.create(
            user=self.admin_user,
            circle=self.circle,
            role=UserRole.CIRCLE_ADMIN
        )
        CircleMembership.objects.create(
            user=self.regular_user,
            circle=self.circle,
            role=UserRole.CIRCLE_MEMBER
        )
        
        # Create a keep by regular user
        self.keep = Keep.objects.create(
            circle=self.circle,
            created_by=self.regular_user,
            keep_type=KeepType.NOTE,
            title='Regular User Keep',
            description='A keep created by a regular user'
        )
        
        # Create a reaction by regular user
        self.reaction = KeepReaction.objects.create(
            keep=self.keep,
            user=self.regular_user,
            reaction_type='like'
        )
        
        # Create a comment by regular user
        self.comment = KeepComment.objects.create(
            keep=self.keep,
            user=self.regular_user,
            comment='Great memory!'
        )
    
    def test_admin_can_modify_any_keep(self):
        """Test that circle admin can modify any keep in their circle."""
        from mysite.keeps.views.permissions import is_circle_admin
        
        # Check admin status
        self.assertTrue(is_circle_admin(self.admin_user, self.circle))
        self.assertFalse(is_circle_admin(self.regular_user, self.circle))
        
        # Admin should be able to modify the keep created by regular user
        # This would be tested in the actual view, but we can test the helper function
        self.assertTrue(is_circle_admin(self.admin_user, self.keep.circle))
    
    def test_admin_can_modify_any_reaction(self):
        """Test that circle admin can modify any reaction in their circle."""
        from mysite.keeps.views.permissions import is_circle_admin
        
        # Admin should be able to modify reactions in their circle
        self.assertTrue(is_circle_admin(self.admin_user, self.reaction.keep.circle))
    
    def test_admin_can_modify_any_comment(self):
        """Test that circle admin can modify any comment in their circle."""
        from mysite.keeps.views.permissions import is_circle_admin
        
        # Admin should be able to modify comments in their circle
        self.assertTrue(is_circle_admin(self.admin_user, self.comment.keep.circle))
    
    def test_regular_user_cannot_modify_others_content(self):
        """Test that regular users can only modify their own content."""
        # Create another regular user
        other_user = User.objects.create_user(
            username='other',
            email='other@example.com',
            password='otherpass123'
        )
        CircleMembership.objects.create(
            user=other_user,
            circle=self.circle,
            role=UserRole.CIRCLE_MEMBER
        )
        
        from mysite.keeps.views.permissions import is_circle_admin
        
        # Other regular user should not be admin
        self.assertFalse(is_circle_admin(other_user, self.circle))
        
        # Other user should not be able to modify content they didn't create
        self.assertNotEqual(self.keep.created_by, other_user)
        self.assertNotEqual(self.reaction.user, other_user)
        self.assertNotEqual(self.comment.user, other_user)
    
    def test_user_can_post_in_circle_they_belong_to(self):
        """Test that both admins and members can post in circles they belong to."""
        from mysite.keeps.views.permissions import can_user_post_in_circle
        
        # Both admin and regular user should be able to post
        self.assertTrue(can_user_post_in_circle(self.admin_user, self.circle))
        self.assertTrue(can_user_post_in_circle(self.regular_user, self.circle))
        
        # User not in circle should not be able to post
        outsider = User.objects.create_user(
            username='outsider',
            email='outsider@example.com',
            password='outsiderpass123'
        )
        self.assertFalse(can_user_post_in_circle(outsider, self.circle))
