"""Tests for pet profile functionality."""
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from users.models import Circle, CircleMembership, PetProfile, PetType, User, UserRole


class PetProfileModelTests(TestCase):
    """Test pet profile model functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123'
        )
        self.circle = Circle.objects.create(name='Test Circle', created_by=self.user)
        CircleMembership.objects.create(user=self.user, circle=self.circle, role=UserRole.CIRCLE_ADMIN)

    def test_pet_creation(self):
        """Test creating a pet profile."""
        pet = PetProfile.objects.create(
            circle=self.circle,
            name='Buddy',
            pet_type=PetType.DOG,
            breed='Golden Retriever'
        )
        
        self.assertEqual(pet.name, 'Buddy')
        self.assertEqual(pet.pet_type, PetType.DOG)
        self.assertEqual(pet.breed, 'Golden Retriever')
        self.assertTrue(pet.is_active)
        self.assertEqual(str(pet), 'Buddy (Dog)')

    def test_pet_age_calculation(self):
        """Test pet age calculation methods."""
        from datetime import date, timedelta
        
        # Pet born 2 years ago
        birthdate = date.today() - timedelta(days=730)
        pet = PetProfile.objects.create(
            circle=self.circle,
            name='Old Dog',
            pet_type=PetType.DOG,
            birthdate=birthdate
        )
        
        self.assertEqual(pet.age_in_days, 730)
        self.assertIn('2 years', pet.display_age)

    def test_pet_without_birthdate(self):
        """Test pet age methods when no birthdate is set."""
        pet = PetProfile.objects.create(
            circle=self.circle,
            name='Mystery Cat',
            pet_type=PetType.CAT
        )
        
        self.assertIsNone(pet.age_in_days)
        self.assertIsNone(pet.display_age)


class PetProfileViewTests(TestCase):
    """Test pet profile API views."""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create admin user
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='password123',
            email_verified=True
        )
        
        # Create member user
        self.member = User.objects.create_user(
            username='member',
            email='member@example.com', 
            password='password123'
        )
        
        # Create circle
        self.circle = Circle.objects.create(name='Pet Circle', created_by=self.admin)
        CircleMembership.objects.create(user=self.admin, circle=self.circle, role=UserRole.CIRCLE_ADMIN)
        CircleMembership.objects.create(user=self.member, circle=self.circle, role=UserRole.CIRCLE_MEMBER)

    def test_list_pets_as_member(self):
        """Test that circle members can view pets."""
        # Create a pet
        pet = PetProfile.objects.create(
            circle=self.circle,
            name='Fluffy',
            pet_type=PetType.CAT
        )
        
        self.client.force_authenticate(user=self.member)
        response = self.client.get(reverse('circle-pet-list', args=[self.circle.id]))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get('data', response.data)
        self.assertEqual(len(data['pets']), 1)
        self.assertEqual(data['pets'][0]['name'], 'Fluffy')

    def test_list_pets_exclude_inactive(self):
        """Test that inactive pets are excluded by default."""
        # Create active and inactive pets
        PetProfile.objects.create(
            circle=self.circle,
            name='Active Pet',
            pet_type=PetType.DOG,
            is_active=True
        )
        PetProfile.objects.create(
            circle=self.circle,
            name='Inactive Pet',
            pet_type=PetType.CAT,
            is_active=False
        )
        
        self.client.force_authenticate(user=self.member)
        response = self.client.get(reverse('circle-pet-list', args=[self.circle.id]))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get('data', response.data)
        self.assertEqual(len(data['pets']), 1)
        self.assertEqual(data['pets'][0]['name'], 'Active Pet')

    def test_list_pets_include_inactive(self):
        """Test including inactive pets with query parameter."""
        # Create active and inactive pets
        PetProfile.objects.create(
            circle=self.circle,
            name='Active Pet',
            pet_type=PetType.DOG,
            is_active=True
        )
        PetProfile.objects.create(
            circle=self.circle,
            name='Inactive Pet',
            pet_type=PetType.CAT,
            is_active=False
        )
        
        self.client.force_authenticate(user=self.member)
        response = self.client.get(reverse('circle-pet-list', args=[self.circle.id]) + '?include_inactive=true')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get('data', response.data)
        self.assertEqual(len(data['pets']), 2)

    def test_create_pet_as_admin(self):
        """Test that circle admins can create pets."""
        pet_data = {
            'name': 'Rex',
            'pet_type': PetType.DOG,
            'breed': 'German Shepherd',
            'bio': 'A loyal companion'
        }
        
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(reverse('circle-pet-list', args=[self.circle.id]), pet_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['data']['pet']['name'], 'Rex')
        
        # Verify pet was created in database
        pet = PetProfile.objects.get(name='Rex')
        self.assertEqual(pet.circle, self.circle)
        self.assertEqual(pet.pet_type, PetType.DOG)

    def test_create_pet_as_member_forbidden(self):
        """Test that circle members cannot create pets."""
        pet_data = {
            'name': 'Mittens',
            'pet_type': PetType.CAT
        }
        
        self.client.force_authenticate(user=self.member)
        response = self.client.post(reverse('circle-pet-list', args=[self.circle.id]), pet_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_pet_details(self):
        """Test getting individual pet details."""
        pet = PetProfile.objects.create(
            circle=self.circle,
            name='Spot',
            pet_type=PetType.DOG,
            breed='Dalmatian'
        )
        
        self.client.force_authenticate(user=self.member)
        response = self.client.get(reverse('pet-detail', args=[pet.id]))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get('data', response.data)
        self.assertEqual(data['pet']['name'], 'Spot')
        self.assertEqual(data['pet']['breed'], 'Dalmatian')

    def test_update_pet_as_admin(self):
        """Test that admins can update pet profiles."""
        pet = PetProfile.objects.create(
            circle=self.circle,
            name='Whiskers',
            pet_type=PetType.CAT
        )
        
        update_data = {'bio': 'Updated bio for Whiskers'}
        
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(reverse('pet-detail', args=[pet.id]), update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['pet']['bio'], 'Updated bio for Whiskers')

    def test_update_pet_as_member_forbidden(self):
        """Test that members cannot update pet profiles."""
        pet = PetProfile.objects.create(
            circle=self.circle,
            name='Nibbles',
            pet_type=PetType.RABBIT
        )
        
        update_data = {'bio': 'Unauthorized update'}
        
        self.client.force_authenticate(user=self.member)
        response = self.client.patch(reverse('pet-detail', args=[pet.id]), update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_pet_as_admin(self):
        """Test that admins can delete pets."""
        pet = PetProfile.objects.create(
            circle=self.circle,
            name='Goldie',
            pet_type=PetType.FISH
        )
        
        self.client.force_authenticate(user=self.admin)
        response = self.client.delete(reverse('pet-detail', args=[pet.id]))
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(PetProfile.objects.filter(id=pet.id).exists())

    def test_non_member_cannot_access_pets(self):
        """Test that non-circle members cannot access pets."""
        outsider = User.objects.create_user(
            username='outsider',
            email='outsider@example.com',
            password='password123'
        )
        
        self.client.force_authenticate(user=outsider)
        response = self.client.get(reverse('circle-pet-list', args=[self.circle.id]))
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class PetProfileSerializerTests(TestCase):
    """Test pet profile serializers."""
    
    def test_pet_name_validation(self):
        """Test pet name validation."""
        from users.serializers.pets import PetProfileCreateSerializer
        
        # Test completely empty name
        data = {'name': '', 'pet_type': PetType.DOG}
        serializer = PetProfileCreateSerializer(data=data)
        
        self.assertFalse(serializer.is_valid())
        self.assertIn('Pet name cannot be empty', str(serializer.errors['name']))
        
        # Test whitespace-only name (custom validation)
        data = {'name': '   ', 'pet_type': PetType.DOG}
        serializer = PetProfileCreateSerializer(data=data)
        
        self.assertFalse(serializer.is_valid())
        self.assertIn('Pet name cannot be empty', str(serializer.errors['name']))
        
        # Test valid name with whitespace
        data = {'name': '  Buddy  ', 'pet_type': PetType.DOG}
        serializer = PetProfileCreateSerializer(data=data)
        
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['name'], 'Buddy')

    def test_pet_profile_serializer_includes_computed_fields(self):
        """Test that serializer includes computed fields."""
        from users.serializers.pets import PetProfileSerializer
        from datetime import date, timedelta
        
        user = User.objects.create_user(username='test', email='test@example.com', password='pass')
        circle = Circle.objects.create(name='Test', created_by=user)
        
        pet = PetProfile.objects.create(
            circle=circle,
            name='Test Pet',
            pet_type=PetType.DOG,
            birthdate=date.today() - timedelta(days=365)
        )
        
        serializer = PetProfileSerializer(pet)
        data = serializer.data
        
        self.assertIn('pet_type_display', data)
        self.assertIn('age_in_days', data)
        self.assertIn('display_age', data)
        self.assertEqual(data['pet_type_display'], 'Dog')
        self.assertEqual(data['age_in_days'], 365)