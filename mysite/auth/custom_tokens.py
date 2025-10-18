"""Custom JWT token implementations with circle information.

This module provides custom JWT token classes that include user's circle
memberships and admin status for each circle in the token payload.
"""
from rest_framework_simplejwt.tokens import RefreshToken

from mysite.users.models import UserRole


class CustomRefreshToken(RefreshToken):
    """Custom refresh token that includes circle membership information.
    
    Extends the default RefreshToken to include:
    - circle_ids: List of all circle IDs the user is a member of
    - admin_circle_ids: List of circle IDs where the user has admin role
    """
    
    @classmethod
    def for_user(cls, user):
        """Create a refresh token for the given user with circle information.
        
        Args:
            user: The User instance to create a token for
            
        Returns:
            CustomRefreshToken instance with circle data in the payload
        """
        token = super().for_user(user)
        
        # Get all circle memberships for the user
        memberships = user.circle_memberships.select_related('circle').all()
        
        # Extract circle IDs and admin circle IDs
        circle_ids = []
        admin_circle_ids = []
        
        for membership in memberships:
            circle_ids.append(membership.circle.id)
            if membership.role == UserRole.CIRCLE_ADMIN:
                admin_circle_ids.append(membership.circle.id)
        
        # Add circle information to token payload
        token['circle_ids'] = circle_ids
        token['admin_circle_ids'] = admin_circle_ids
        
        return token