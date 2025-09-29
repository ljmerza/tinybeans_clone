"""Pet profile models for family pets.

This module defines models for managing pet profiles within circles.
Unlike child profiles, pet profiles can never be upgraded to user accounts.
"""
import uuid
from django.core.validators import MinLengthValidator
from django.db import models
from django.utils import timezone

from .circle import Circle


class PetType(models.TextChoices):
    """Types of pets supported in the system.
    
    Common pet types with room for expansion.
    """
    DOG = 'dog', 'Dog'
    CAT = 'cat', 'Cat' 
    BIRD = 'bird', 'Bird'
    FISH = 'fish', 'Fish'
    RABBIT = 'rabbit', 'Rabbit'
    HAMSTER = 'hamster', 'Hamster'
    GUINEA_PIG = 'guinea_pig', 'Guinea Pig'
    REPTILE = 'reptile', 'Reptile'
    HORSE = 'horse', 'Horse'
    OTHER = 'other', 'Other'


class PetProfile(models.Model):
    """Profile for a family pet within a circle.
    
    Represents a pet's profile with basic information. Pets cannot be
    upgraded to user accounts and are permanently linked to their circle.
    
    Attributes:
        id: UUID primary key for secure identification
        circle: The family circle this pet belongs to
        name: Pet's name as shown in the app
        pet_type: Type of pet (dog, cat, etc.)
        breed: Pet's breed (optional)
        birthdate: Pet's date of birth or adoption date (optional)
        avatar_url: URL to pet's profile picture (optional)
        bio: Short description or personality notes (optional)
        is_active: Whether the pet profile is active (false if pet passed away)
        created_at: When the profile was created
        updated_at: When the profile was last modified
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    circle = models.ForeignKey(Circle, on_delete=models.CASCADE, related_name='pets')
    name = models.CharField(max_length=150, validators=[MinLengthValidator(1)])
    pet_type = models.CharField(max_length=20, choices=PetType.choices)
    breed = models.CharField(max_length=100, blank=True)
    birthdate = models.DateField(blank=True, null=True)
    avatar_url = models.URLField(blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_pet_type_display()})"

    @property
    def age_in_days(self):
        """Calculate pet's age in days if birthdate is set."""
        if self.birthdate:
            return (timezone.now().date() - self.birthdate).days
        return None

    @property
    def display_age(self):
        """Get a human-readable age string."""
        if not self.birthdate:
            return None
        
        age_days = self.age_in_days
        if age_days is None:
            return None
        
        years = age_days // 365
        months = (age_days % 365) // 30
        
        if years > 0:
            if months > 0:
                return f"{years} year{'s' if years != 1 else ''}, {months} month{'s' if months != 1 else ''}"
            else:
                return f"{years} year{'s' if years != 1 else ''}"
        elif months > 0:
            return f"{months} month{'s' if months != 1 else ''}"
        else:
            return f"{age_days} day{'s' if age_days != 1 else ''}"