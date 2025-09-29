"""Serializers for pet profile management."""
from __future__ import annotations

from rest_framework import serializers

from ..models import PetProfile, PetType


class PetProfileSerializer(serializers.ModelSerializer):
    """Serializer for pet profiles with computed fields."""
    
    age_in_days = serializers.ReadOnlyField()
    display_age = serializers.ReadOnlyField()
    pet_type_display = serializers.CharField(source='get_pet_type_display', read_only=True)
    
    class Meta:
        model = PetProfile
        fields = [
            'id',
            'name', 
            'pet_type',
            'pet_type_display',
            'breed',
            'birthdate',
            'avatar_url',
            'bio',
            'favorite_moments',
            'is_active',
            'age_in_days',
            'display_age',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PetProfileCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating pet profiles."""
    
    name = serializers.CharField(allow_blank=True)  # Allow blank so we can validate in validate_name
    
    class Meta:
        model = PetProfile
        fields = [
            'name',
            'pet_type', 
            'breed',
            'birthdate',
            'avatar_url',
            'bio',
            'is_active',
        ]
        
    def validate_name(self, value):
        """Ensure pet name is not empty after stripping whitespace."""
        stripped_name = value.strip() if value else ""
        if not stripped_name:
            raise serializers.ValidationError("Pet name cannot be empty.")
        return stripped_name

    def create(self, validated_data):
        """Create pet profile with circle from context."""
        circle = self.context['circle']
        return PetProfile.objects.create(circle=circle, **validated_data)


__all__ = [
    'PetProfileSerializer',
    'PetProfileCreateSerializer',
]