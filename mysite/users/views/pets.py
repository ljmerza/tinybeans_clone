"""Pet profile management views."""
from __future__ import annotations

from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiResponse, OpenApiTypes, extend_schema

from ..models import Circle, CircleMembership, PetProfile, UserRole
from ..serializers import PetProfileSerializer, PetProfileCreateSerializer


class CirclePetListView(APIView):
    """List and create pets for a specific circle."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PetProfileSerializer

    @extend_schema(
        description='List all pets in a circle. Only circle members can view pets.',
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description='List of pets in the circle.',
            )
        }
    )
    def get(self, request, circle_id):
        """List all pets in the circle."""
        circle = get_object_or_404(Circle, id=circle_id)
        
        # Check if user is a member of the circle
        membership = CircleMembership.objects.filter(circle=circle, user=request.user).first()
        if not (request.user.is_superuser or membership):
            raise PermissionDenied(_('Only circle members can view pets'))
        
        # Get active pets by default, include inactive if requested
        include_inactive = request.query_params.get('include_inactive', '').lower() == 'true'
        pets = circle.pets.all()
        if not include_inactive:
            pets = pets.filter(is_active=True)
            
        pets = pets.order_by('name')
        serializer = PetProfileSerializer(pets, many=True)
        return Response({'pets': serializer.data})

    @extend_schema(
        description='Add a new pet to the circle. Only circle admins can add pets.',
        request=PetProfileCreateSerializer,
        responses={
            201: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description='Pet created successfully.',
            )
        },
    )
    def post(self, request, circle_id):
        """Create a new pet in the circle."""
        circle = get_object_or_404(Circle, id=circle_id)
        
        # Check if user is a circle admin
        membership = CircleMembership.objects.filter(circle=circle, user=request.user).first()
        if not (request.user.is_superuser or (membership and membership.role == UserRole.CIRCLE_ADMIN)):
            raise PermissionDenied(_('Only circle admins can add pets'))
        
        serializer = PetProfileCreateSerializer(data=request.data, context={'circle': circle})
        serializer.is_valid(raise_exception=True)
        pet = serializer.save()
        
        # Return the full pet data
        response_serializer = PetProfileSerializer(pet)
        return Response({'pet': response_serializer.data}, status=status.HTTP_201_CREATED)


class PetProfileDetailView(APIView):
    """View, update, and delete individual pet profiles."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PetProfileSerializer

    def _get_pet_and_check_permission(self, pet_id, user, admin_required=False):
        """Helper to get pet and check user permissions."""
        pet = get_object_or_404(PetProfile, id=pet_id)
        membership = CircleMembership.objects.filter(circle=pet.circle, user=user).first()
        
        if not (user.is_superuser or membership):
            raise PermissionDenied(_('Only circle members can access pets'))
            
        if admin_required and not (user.is_superuser or (membership and membership.role == UserRole.CIRCLE_ADMIN)):
            raise PermissionDenied(_('Only circle admins can modify pets'))
            
        return pet

    @extend_schema(
        description='Get details of a specific pet.',
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description='Pet details.',
            )
        }
    )
    def get(self, request, pet_id):
        """Get pet details."""
        pet = self._get_pet_and_check_permission(pet_id, request.user)
        serializer = PetProfileSerializer(pet)
        return Response({'pet': serializer.data})

    @extend_schema(
        description='Update pet profile. Only circle admins can update pets.',
        request=PetProfileSerializer,
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description='Pet updated successfully.',
            )
        },
    )
    def patch(self, request, pet_id):
        """Update pet profile."""
        pet = self._get_pet_and_check_permission(pet_id, request.user, admin_required=True)
        
        serializer = PetProfileSerializer(pet, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({'pet': serializer.data})

    @extend_schema(
        description='Delete a pet profile. Only circle admins can delete pets.',
        responses={204: OpenApiResponse(description='Pet deleted successfully.')},
    )
    def delete(self, request, pet_id):
        """Delete pet profile."""
        pet = self._get_pet_and_check_permission(pet_id, request.user, admin_required=True)
        pet.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)