"""Per-circle in-app AI settings and scan status."""

from django.conf import settings
from django.db import models


class CircleAiSettings(models.Model):
    """Whether a circle's captions go to the operator's AI model for milestone picks, and how the last scan went.

    The endpoint, key and model are the operator's (env, see
    ``mysite.config.settings.ai``); nothing here names them, and no secret is
    stored. A row is made the first time an admin changes the setting.

    Attributes:
        circle: The circle; also the primary key
        enabled: Turned on by a circle admin (or off by a superuser in Django admin)
        acknowledged_by: The admin who accepted the data-sharing notice when turning it on
        acknowledged_at: When they did
        last_run_at: When the last scan of this circle ended
        last_success_at: When a scan last ended without a provider error
        last_error: A fixed code from the last scan (``mysite.ai.client`` codes,
            ``pending_cap`` or ``time_limit``); empty when it went fine
        updated_by: Who last changed ``enabled``
        updated_at: When the row last changed
    """

    circle = models.OneToOneField(
        "users.Circle", on_delete=models.CASCADE, primary_key=True, related_name="ai_settings"
    )
    enabled = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=30, blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "circle AI settings"
        verbose_name_plural = "circle AI settings"

    def __str__(self):
        return f"AI settings of {self.circle}"
