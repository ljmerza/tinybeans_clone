"""Tests for response_utils module"""
import pytest
from rest_framework import status

from auth.response_utils import rate_limit_response, error_response, success_response


class TestResponseUtils:
    """Test response utility functions"""

    def test_rate_limit_response_default_message(self):
        """Test rate_limit_response with default message"""
        response = rate_limit_response()
        
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert response.data == {'error': 'Too many requests. Please try again later.'}

    def test_rate_limit_response_custom_message(self):
        """Test rate_limit_response with custom message"""
        custom_message = 'Account temporarily locked due to too many failed attempts.'
        response = rate_limit_response(custom_message)
        
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert response.data == {'error': custom_message}

    def test_error_response_default_status(self):
        """Test error_response with default status code"""
        response = error_response('Invalid input')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == {'error': 'Invalid input'}

    def test_error_response_custom_status(self):
        """Test error_response with custom status code"""
        response = error_response('Not found', status.HTTP_404_NOT_FOUND)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data == {'error': 'Not found'}

    def test_success_response_default_status(self):
        """Test success_response with default status code"""
        data = {'message': 'Operation successful', 'id': 123}
        response = success_response(data)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data == data

    def test_success_response_custom_status(self):
        """Test success_response with custom status code"""
        data = {'id': 456, 'created': True}
        response = success_response(data, status.HTTP_201_CREATED)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data == data
