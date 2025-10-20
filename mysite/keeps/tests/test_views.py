"""Tests for Keep API views."""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from mysite.circles.models import Circle, CircleMembership
from mysite.users.models import UserRole
from mysite.keeps.models import Keep, KeepType, KeepReaction, KeepComment

User = get_user_model()


@pytest.fixture
def api_client():
    """Create an API client."""
    return APIClient()


@pytest.fixture
def user():
    """Create a test user."""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def other_user():
    """Create another test user."""
    return User.objects.create_user(
        username='otheruser',
        email='other@example.com',
        password='otherpass123'
    )


@pytest.fixture
def circle(user):
    """Create a test circle."""
    circle = Circle.objects.create(
        name='Test Family',
        created_by=user
    )
    CircleMembership.objects.create(
        user=user,
        circle=circle,
        role=UserRole.CIRCLE_ADMIN
    )
    return circle


@pytest.fixture
def other_circle(other_user):
    """Create another circle."""
    circle = Circle.objects.create(
        name='Other Family',
        created_by=other_user
    )
    CircleMembership.objects.create(
        user=other_user,
        circle=circle
    )
    return circle


@pytest.fixture
def keep(user, circle):
    """Create a test keep."""
    return Keep.objects.create(
        circle=circle,
        created_by=user,
        keep_type=KeepType.NOTE,
        title='Test Memory',
        description='A wonderful memory'
    )


@pytest.mark.django_db
class TestKeepListCreateView:
    """Test Keep list and create views."""
    
    def test_list_keeps_requires_authentication(self, api_client):
        """Test that listing keeps requires authentication."""
        response = api_client.get('/api/keeps/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_list_keeps_returns_user_circles_keeps(self, api_client, user, circle, keep):
        """Test that listing keeps returns only keeps from user's circles."""
        api_client.force_authenticate(user=user)
        response = api_client.get('/api/keeps/')
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['id'] == str(keep.id)
    
    def test_list_keeps_excludes_other_circles(self, api_client, user, circle, keep, other_user, other_circle):
        """Test that keeps from other circles are not visible."""
        # Create a keep in another circle
        other_keep = Keep.objects.create(
            circle=other_circle,
            created_by=other_user,
            keep_type=KeepType.NOTE,
            title='Private Memory'
        )
        
        api_client.force_authenticate(user=user)
        response = api_client.get('/api/keeps/')
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['id'] == str(keep.id)
    
    def test_create_keep(self, api_client, user, circle):
        """Test creating a new keep."""
        api_client.force_authenticate(user=user)
        
        data = {
            'circle': str(circle.id),
            'keep_type': KeepType.NOTE,
            'title': 'New Memory',
            'description': 'A brand new memory',
            'tags': 'new,test'
        }
        
        response = api_client.post('/api/keeps/', data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['title'] == 'New Memory'
        assert response.data['created_by_username'] == user.username
        
        # Verify keep was created
        keep = Keep.objects.get(id=response.data['id'])
        assert keep.title == 'New Memory'
        assert keep.created_by == user
    
    def test_create_keep_requires_circle_membership(self, api_client, user, other_circle):
        """Test that user cannot create keep in circle they don't belong to."""
        api_client.force_authenticate(user=user)
        
        data = {
            'circle': str(other_circle.id),
            'keep_type': KeepType.NOTE,
            'title': 'Unauthorized',
        }
        
        response = api_client.post('/api/keeps/', data, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_filter_by_keep_type(self, api_client, user, circle):
        """Test filtering keeps by type."""
        # Create keeps of different types
        note_keep = Keep.objects.create(
            circle=circle,
            created_by=user,
            keep_type=KeepType.NOTE,
            title='Note'
        )
        media_keep = Keep.objects.create(
            circle=circle,
            created_by=user,
            keep_type=KeepType.MEDIA,
            title='Photo'
        )
        
        api_client.force_authenticate(user=user)
        
        # Filter for notes
        response = api_client.get(f'/api/keeps/?keep_type={KeepType.NOTE}')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['keep_type'] == KeepType.NOTE
    
    def test_filter_by_tag(self, api_client, user, circle):
        """Test filtering keeps by tag."""
        keep1 = Keep.objects.create(
            circle=circle,
            created_by=user,
            keep_type=KeepType.NOTE,
            title='Summer',
            tags='summer,vacation'
        )
        keep2 = Keep.objects.create(
            circle=circle,
            created_by=user,
            keep_type=KeepType.NOTE,
            title='Winter',
            tags='winter,snow'
        )
        
        api_client.force_authenticate(user=user)
        
        response = api_client.get('/api/keeps/?tag=summer')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert 'summer' in response.data[0]['tags']


@pytest.mark.django_db
class TestKeepDetailView:
    """Test Keep detail, update, and delete views."""
    
    def test_retrieve_keep(self, api_client, user, keep):
        """Test retrieving a single keep."""
        api_client.force_authenticate(user=user)
        response = api_client.get(f'/api/keeps/{keep.id}/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(keep.id)
        assert response.data['title'] == keep.title
    
    def test_update_own_keep(self, api_client, user, keep):
        """Test that user can update their own keep."""
        api_client.force_authenticate(user=user)
        
        data = {
            'title': 'Updated Title',
            'description': 'Updated description'
        }
        
        response = api_client.patch(f'/api/keeps/{keep.id}/', data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == 'Updated Title'
        
        keep.refresh_from_db()
        assert keep.title == 'Updated Title'
    
    def test_delete_own_keep(self, api_client, user, keep):
        """Test that user can delete their own keep."""
        api_client.force_authenticate(user=user)
        
        response = api_client.delete(f'/api/keeps/{keep.id}/')
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Keep.objects.filter(id=keep.id).exists()
    
    def test_regular_user_cannot_update_others_keep(self, api_client, user, circle, other_user):
        """Test that regular users cannot update others' keeps."""
        # Add other_user to circle as member
        CircleMembership.objects.create(
            user=other_user,
            circle=circle,
            role=UserRole.CIRCLE_MEMBER
        )
        
        # Create keep by user
        keep = Keep.objects.create(
            circle=circle,
            created_by=user,
            keep_type=KeepType.NOTE,
            title='Original'
        )
        
        # Try to update as other_user
        api_client.force_authenticate(user=other_user)
        data = {'title': 'Hacked'}
        response = api_client.patch(f'/api/keeps/{keep.id}/', data, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_circle_admin_can_update_any_keep(self, api_client, user, circle, other_user):
        """Test that circle admin can update any keep in their circle."""
        # Add other_user to circle as member
        CircleMembership.objects.create(
            user=other_user,
            circle=circle,
            role=UserRole.CIRCLE_MEMBER
        )
        
        # Create keep by other_user
        keep = Keep.objects.create(
            circle=circle,
            created_by=other_user,
            keep_type=KeepType.NOTE,
            title='Original'
        )
        
        # Update as admin (user)
        api_client.force_authenticate(user=user)
        data = {'title': 'Admin Updated'}
        response = api_client.patch(f'/api/keeps/{keep.id}/', data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == 'Admin Updated'


@pytest.mark.django_db
class TestReactionViews:
    """Test Keep reaction views."""
    
    def test_add_reaction(self, api_client, user, keep):
        """Test adding a reaction to a keep."""
        api_client.force_authenticate(user=user)
        
        data = {'reaction_type': 'like'}
        response = api_client.post(f'/api/keeps/{keep.id}/reactions/', data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert KeepReaction.objects.filter(keep=keep, user=user, reaction_type='like').exists()
    
    def test_list_reactions(self, api_client, user, keep):
        """Test listing reactions for a keep."""
        # Add reaction
        KeepReaction.objects.create(keep=keep, user=user, reaction_type='like')
        
        api_client.force_authenticate(user=user)
        response = api_client.get(f'/api/keeps/{keep.id}/reactions/')
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
    
    def test_remove_reaction(self, api_client, user, keep):
        """Test removing a reaction."""
        reaction = KeepReaction.objects.create(keep=keep, user=user, reaction_type='like')
        
        api_client.force_authenticate(user=user)
        response = api_client.delete(f'/api/keeps/{keep.id}/reactions/{reaction.id}/')
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not KeepReaction.objects.filter(id=reaction.id).exists()


@pytest.mark.django_db
class TestCommentViews:
    """Test Keep comment views."""
    
    def test_add_comment(self, api_client, user, keep):
        """Test adding a comment to a keep."""
        api_client.force_authenticate(user=user)
        
        data = {'comment': 'Great memory!'}
        response = api_client.post(f'/api/keeps/{keep.id}/comments/', data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert KeepComment.objects.filter(keep=keep, user=user).exists()
    
    def test_list_comments(self, api_client, user, keep):
        """Test listing comments for a keep."""
        # Add comment
        KeepComment.objects.create(keep=keep, user=user, comment='Nice!')
        
        api_client.force_authenticate(user=user)
        response = api_client.get(f'/api/keeps/{keep.id}/comments/')
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
    
    def test_update_own_comment(self, api_client, user, keep):
        """Test updating own comment."""
        comment = KeepComment.objects.create(keep=keep, user=user, comment='Original')
        
        api_client.force_authenticate(user=user)
        data = {'comment': 'Updated'}
        response = api_client.patch(f'/api/keeps/{keep.id}/comments/{comment.id}/', data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        comment.refresh_from_db()
        assert comment.comment == 'Updated'
    
    def test_delete_own_comment(self, api_client, user, keep):
        """Test deleting own comment."""
        comment = KeepComment.objects.create(keep=keep, user=user, comment='Delete me')
        
        api_client.force_authenticate(user=user)
        response = api_client.delete(f'/api/keeps/{keep.id}/comments/{comment.id}/')
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not KeepComment.objects.filter(id=comment.id).exists()
