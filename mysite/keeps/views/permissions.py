"""Permission classes for keeps app."""
from rest_framework import permissions

from users.models import Circle, CircleMembership, UserRole


class IsCircleMember(permissions.BasePermission):
    """Permission to check if user is a member of the circle."""
    
    def has_permission(self, request, view):
        """Check if user is authenticated."""
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        """Check if user is a member of the circle containing the object."""
        # For Keep objects
        if hasattr(obj, 'circle'):
            circle = obj.circle
        # For related objects (comments, reactions, etc.)
        elif hasattr(obj, 'keep'):
            circle = obj.keep.circle
        else:
            return False
        
        return CircleMembership.objects.filter(
            user=request.user,
            circle=circle
        ).exists()


class IsCircleAdminOrOwner(permissions.BasePermission):
    """Permission to check if user is circle admin or owner of the object."""
    
    def has_permission(self, request, view):
        """Check if user is authenticated."""
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        """Check if user can modify this object."""
        # For Keep objects
        if hasattr(obj, 'circle'):
            circle = obj.circle
            owner_field = 'created_by'
        # For related objects (comments, reactions, etc.)
        elif hasattr(obj, 'keep'):
            circle = obj.keep.circle
            owner_field = 'user'
        else:
            return False
        
        # First check if user is a member of the circle
        try:
            membership = CircleMembership.objects.get(
                user=request.user,
                circle=circle
            )
        except CircleMembership.DoesNotExist:
            return False
        
        # Allow if user is circle admin
        if membership.role == UserRole.CIRCLE_ADMIN:
            return True
        
        # Allow if user is the owner of the object
        owner = getattr(obj, owner_field, None)
        return owner == request.user


def is_circle_admin(user, circle):
    """Check if user is an admin of the given circle."""
    try:
        membership = CircleMembership.objects.get(user=user, circle=circle)
        return membership.role == UserRole.CIRCLE_ADMIN
    except CircleMembership.DoesNotExist:
        return False


def can_user_post_in_circle(user, circle):
    """Check if user can post keeps in the given circle (member or admin)."""
    return CircleMembership.objects.filter(
        user=user,
        circle=circle
    ).exists()
