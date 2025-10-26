"""API tests for recovery code generation and download endpoints."""

import pytest
from unittest.mock import patch
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from mysite.auth.models import RecoveryCode, TwoFactorSettings
from .helpers import response_payload

User = get_user_model()

pytestmark = pytest.mark.django_db


class TestRecoveryCodeAPI:
    """Test recovery code endpoints"""
    
    def setup_method(self):
        """Set up test client and user"""
        self.client = APIClient()
        self.user = User.objects.create_user(email='testuser@example.com', password='testpass')
        self.client.force_authenticate(user=self.user)
    
    @patch('mysite.auth.services.twofa_service.TwoFactorService.generate_recovery_codes')
    def test_generate_recovery_codes_success(self, mock_generate):
        """Test recovery code generation"""
        TwoFactorSettings.objects.create(
            user=self.user,
            is_enabled=True
        )
        
        mock_codes = [f'CODE-{i:04d}-TEST' for i in range(10)]
        mock_generate.return_value = mock_codes
        
        response = self.client.post('/api/auth/2fa/recovery-codes/generate/')
        
        assert response.status_code == status.HTTP_200_OK
        payload = response_payload(response)
        assert len(payload['recovery_codes']) == 10
    
    def test_generate_recovery_codes_not_enabled(self):
        """Test recovery code generation when 2FA not enabled"""
        TwoFactorSettings.objects.create(
            user=self.user,
            is_enabled=False
        )
        
        response = self.client.post('/api/auth/2fa/recovery-codes/generate/')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_download_recovery_codes_txt(self):
        """Test downloading recovery codes as TXT"""
        TwoFactorSettings.objects.create(
            user=self.user,
            is_enabled=True
        )
        
        # Create recovery codes - these will be sent in the request body
        codes = [f'CODE-{i:04d}-TEST' for i in range(5)]
        for code in codes:
            RecoveryCode.objects.create(
                user=self.user,
                code=code
            )
        
        response = self.client.post(
            '/api/auth/2fa/recovery-codes/download/',
            {'format': 'txt', 'codes': codes},
            content_type='application/json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response['Content-Type'] == 'text/plain'
        assert 'tinybeans-recovery-codes.txt' in response['Content-Disposition']
    
    @patch('mysite.auth.services.recovery_code_service.RecoveryCodeService.export_as_pdf')
    def test_download_recovery_codes_pdf(self, mock_pdf):
        """Test downloading recovery codes as PDF"""
        TwoFactorSettings.objects.create(
            user=self.user,
            is_enabled=True
        )
        
        # Create recovery codes - these will be sent in the request body
        codes = [f'CODE-{i:04d}-TEST' for i in range(5)]
        for code in codes:
            RecoveryCode.objects.create(
                user=self.user,
                code=code
            )
        
        mock_pdf.return_value = b'fake-pdf-content'
        
        response = self.client.post(
            '/api/auth/2fa/recovery-codes/download/',
            {'format': 'pdf', 'codes': codes},
            content_type='application/json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response['Content-Type'] == 'application/pdf'
        assert 'tinybeans-recovery-codes.pdf' in response['Content-Disposition']
    
    def test_download_no_codes(self):
        """Test download when no codes available"""
        response = self.client.post(
            '/api/auth/2fa/recovery-codes/download/',
            {'format': 'txt', 'codes': []},
            content_type='application/json'
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
