"""Circle-related asynchronous tasks."""

from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db import models
from django.utils import timezone

from mysite.auth.token_utils import TOKEN_TTL_SECONDS, store_token
from mysite.emails.tasks import send_email_task
from mysite.emails.templates import CIRCLE_INVITATION_REMINDER_TEMPLATE

from .models import CircleInvitation, CircleInvitationStatus

__all__ = ['send_circle_invitation_reminders']


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={'max_retries': 3},
    queue='maintenance',
)
def send_circle_invitation_reminders(self):
    """Send reminder emails for pending circle invitations."""
    delay_minutes = getattr(settings, 'CIRCLE_INVITE_REMINDER_DELAY_MINUTES', 1440)
    cooldown_minutes = getattr(settings, 'CIRCLE_INVITE_REMINDER_COOLDOWN_MINUTES', 1440)
    batch_size = getattr(settings, 'CIRCLE_INVITE_REMINDER_BATCH_SIZE', 100)
    if delay_minutes <= 0 or batch_size <= 0:
        return 0

    now = timezone.now()
    cutoff = now - timedelta(minutes=delay_minutes)
    cooldown_cutoff = now - timedelta(minutes=cooldown_minutes) if cooldown_minutes > 0 else now

    invitations = (
        CircleInvitation.objects.select_related('circle', 'invited_by')
        .filter(
            status=CircleInvitationStatus.PENDING,
            created_at__lte=cutoff,
        )
        .filter(
            models.Q(reminder_sent_at__isnull=True)
            | models.Q(reminder_sent_at__lte=cooldown_cutoff)
        )
        .order_by('reminder_sent_at', 'created_at')[:batch_size]
    )

    if not invitations:
        return 0

    base_url = (getattr(settings, 'ACCOUNT_FRONTEND_BASE_URL', 'http://localhost:3000') or 'http://localhost:3000').rstrip('/')
    sent = 0
    for invitation in invitations:
        token = store_token(
            'circle-invite',
            {
                'invitation_id': str(invitation.id),
                'circle_id': invitation.circle_id,
                'email': invitation.email,
                'role': invitation.role,
                'issued_at': now.isoformat(),
                'existing_user': bool(invitation.invited_user_id),
                'invited_user_id': invitation.invited_user_id,
            },
            ttl=TOKEN_TTL_SECONDS,
        )
        invitation_link = f"{base_url}/invitations/accept?token={token}"
        send_email_task.delay(
            to_email=invitation.email,
            template_id=CIRCLE_INVITATION_REMINDER_TEMPLATE,
            context={
                'circle_name': invitation.circle.name,
                'invited_by': invitation.invited_by.username if invitation.invited_by_id else None,
                'invitation_link': invitation_link,
            },
        )
        invitation.reminder_sent_at = now
        invitation.save(update_fields=['reminder_sent_at'])
        sent += 1

    return sent

