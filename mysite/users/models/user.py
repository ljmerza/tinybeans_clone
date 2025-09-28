"""User authentication and role management models.

This module defines the custom User model and related authentication classes
for the Tinybeans application, including user roles and custom user management.
"""
from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserRole(models.TextChoices):
    """User roles within circles.
    
    Defines the different permission levels a user can have within a circle.
    Circle admins have elevated permissions to manage the circle and its members.
    """
    CIRCLE_ADMIN = 'admin', 'Circle Admin'
    CIRCLE_MEMBER = 'member', 'Circle Member'


class UserManager(BaseUserManager):
    """Custom user manager for the User model.
    
    Handles user creation with custom fields and validation.
    Ensures both username and email are required and properly normalized.
    """
    use_in_migrations = True

    def _create_user(self, username, email, password, **extra_fields):
        """Create and save a user with the given username, email and password.
        
        Args:
            username: The username for the user
            email: The email address for the user
            password: The password for the user
            **extra_fields: Additional fields to set on the user
            
        Returns:
            The created User instance
            
        Raises:
            ValueError: If username or email is not provided
        """
        if not username:
            raise ValueError('The username must be set')
        if not email:
            raise ValueError('The email address must be set')
        email = self.normalize_email(email)
        username = self.model.normalize_username(username)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username, email, password=None, **extra_fields):
        """Create a regular user with default permissions.
        
        Args:
            username: The username for the user
            email: The email address for the user
            password: The password for the user (optional)
            **extra_fields: Additional fields to set on the user
            
        Returns:
            The created User instance
        """
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('role', UserRole.CIRCLE_MEMBER)
        return self._create_user(username, email, password, **extra_fields)

    def create_superuser(self, username, email, password=None, **extra_fields):
        """Create a superuser with admin permissions.
        
        Args:
            username: The username for the superuser
            email: The email address for the superuser
            password: The password for the superuser (optional)
            **extra_fields: Additional fields to set on the user
            
        Returns:
            The created User instance
            
        Raises:
            ValueError: If is_staff or is_superuser is not True
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', UserRole.CIRCLE_ADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(username, email, password, **extra_fields)


class User(AbstractUser):
    """Custom user model for the Tinybeans application.
    
    Extends Django's AbstractUser with additional fields for email verification
    and user roles within circles. Email is required and must be unique.
    
    Attributes:
        email: User's email address (required, unique)
        role: User's default role (admin or member)
        email_verified: Whether the user's email has been verified
    """
    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.CIRCLE_MEMBER,
    )
    email_verified = models.BooleanField(default=False)

    objects = UserManager()

    REQUIRED_FIELDS = ['email']

    class Meta:
        ordering = ['username']