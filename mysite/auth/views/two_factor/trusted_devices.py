"""View layer for trusted device management."""

import logging

from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.views import APIView

from mysite.auth.permissions import IsEmailVerified
from mysite.auth.serializers import TrustedDeviceSerializer
from mysite.auth.services.trusted_device_service import TrustedDeviceService
from mysite.notification_utils import (
    create_message,
    error_response,
    success_response,
)


logger = logging.getLogger(__name__)


class TrustedDevicesListView(APIView):
    """List and manage trusted devices"""
    permission_classes = [permissions.IsAuthenticated, IsEmailVerified]
    
    @extend_schema(responses={200: TrustedDeviceSerializer(many=True)})
    def get(self, request):
        """Get all trusted devices"""
        devices = TrustedDeviceService.get_trusted_devices(request.user)
        serializer = TrustedDeviceSerializer(devices, many=True)
        return success_response({'devices': serializer.data})
    
    @extend_schema(
        request={'device_id': 'string'},
        responses={200: dict}
    )
    def delete(self, request):
        """Remove a trusted device"""
        device_id = request.data.get('device_id')
        
        if not device_id:
            return error_response(
                'device_id_required',
                [create_message('errors.twofa.device_id_required')],
                status.HTTP_400_BAD_REQUEST
            )
        
        removed = TrustedDeviceService.remove_trusted_device(request.user, device_id)
        
        if removed:
            return success_response({}, messages=[create_message('notifications.twofa.device_removed')])
        else:
            return error_response(
                'device_not_found',
                [create_message('errors.twofa.device_not_found')],
                status.HTTP_404_NOT_FOUND
            )
    
    @extend_schema(
        responses={201: TrustedDeviceSerializer}
    )
    def post(self, request):
        """Add current device as a trusted device"""
        try:
            trusted_device, token, created = TrustedDeviceService.add_trusted_device(request.user, request)
        except Exception:
            logger.exception("Failed to add trusted device for user %s", request.user.pk)
            return error_response(
                'device_add_failed',
                [create_message('errors.twofa.device_add_failed')],
                status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        serializer = TrustedDeviceSerializer(trusted_device)
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        message_key = (
            'notifications.twofa.device_added'
            if created
            else 'notifications.twofa.device_already_trusted'
        )
        response = success_response(
            {'device': serializer.data, 'created': created},
            messages=[
                create_message(
                    message_key,
                    {'device_name': trusted_device.device_name}
                )
            ],
            status_code=status_code
        )
        TrustedDeviceService.set_trusted_device_cookie(response, token)
        return response

class TrustedDeviceRemoveView(APIView):
    """Remove specific trusted device"""
    permission_classes = [permissions.IsAuthenticated, IsEmailVerified]
    
    @extend_schema(responses={200: dict})
    def delete(self, request, device_id):
        """Remove specific trusted device by ID"""
        removed = TrustedDeviceService.remove_trusted_device(request.user, device_id)
        
        if removed:
            return success_response({}, messages=[create_message('notifications.twofa.device_removed')])
        else:
            return error_response(
                'device_not_found',
                [create_message('errors.twofa.device_not_found')],
                status.HTTP_404_NOT_FOUND
            )
