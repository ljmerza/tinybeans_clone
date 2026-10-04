"""Upload size limits: the client-facing endpoint and the proxy body cap."""

from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient

from mysite.keeps.views.uploads import MAX_POSTER_SIZE, MULTIPART_OVERHEAD, max_upload_request_size

User = get_user_model()

LIMITS_URL = "/api/keeps/upload/limits/"
MB = 1000 * 1000


@pytest.mark.django_db
class TestUploadLimitsView:
    def test_requires_login(self):
        response = APIClient().get(LIMITS_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @override_settings(MAX_UPLOAD_SIZE=95 * MB, MAX_VIDEO_UPLOAD_SIZE=90 * MB)
    def test_reports_the_configured_limits(self):
        client = APIClient()
        client.force_authenticate(User.objects.create_user(email="limits@example.com", password="pw-123456"))

        response = client.get(LIMITS_URL)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"] == {"max_photo_bytes": 95 * MB, "max_video_bytes": 90 * MB}


class TestUploadBodyLimit:
    @override_settings(MAX_UPLOAD_SIZE=100 * MB, MAX_VIDEO_UPLOAD_SIZE=95 * MB)
    def test_covers_the_largest_file_plus_poster(self):
        assert max_upload_request_size() == 100 * MB + MAX_POSTER_SIZE + MULTIPART_OVERHEAD

    @override_settings(MAX_UPLOAD_SIZE=95 * MB, MAX_VIDEO_UPLOAD_SIZE=95 * MB)
    def test_management_command_prints_bytes_for_nginx(self):
        out = StringIO()
        call_command("upload_body_limit", stdout=out)
        assert out.getvalue().strip() == str(95 * MB + MAX_POSTER_SIZE + MULTIPART_OVERHEAD)
