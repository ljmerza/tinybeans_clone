"""Calendar view for browsing keeps one month at a time."""
import re
from datetime import datetime, timezone as dt_timezone

from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiTypes, OpenApiParameter

from mysite.notification_utils import create_message, error_response, success_response
from mysite.circles.models import Circle
from ..models import Keep

MONTH_RE = re.compile(r'^(\d{4})-(\d{2})$')


class KeepCalendarView(APIView):
    """Photo-calendar entries for a single month."""

    @extend_schema(
        summary="Get calendar entries for a month",
        description="Retrieve keeps with photos for a single month, shaped for the "
                    "photo-calendar UI. Only keeps from circles the user belongs to "
                    "are returned; pass circle_slug to restrict to one circle.",
        parameters=[
            OpenApiParameter(
                name='month',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Month to fetch in YYYY-MM format (UTC)',
                required=True
            ),
            OpenApiParameter(
                name='circle_slug',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Optional circle slug to restrict entries to one circle',
                required=False
            )
        ],
        responses={
            200: OpenApiResponse(
                description="Calendar entries for the requested month"
            ),
            400: OpenApiResponse(
                description="Missing or invalid month parameter"
            ),
            404: OpenApiResponse(
                description="Circle not found or user is not a member"
            )
        }
    )
    def get(self, request):
        """Get photo entries for a single month."""
        month_param = request.query_params.get('month', '')
        match = MONTH_RE.match(month_param)
        if not match or not 1 <= int(match.group(2)) <= 12:
            return error_response(
                'invalid_month',
                messages=[create_message('errors.invalid_month')],
                status_code=400
            )

        year, month = int(match.group(1)), int(match.group(2))
        start = datetime(year, month, 1, tzinfo=dt_timezone.utc)
        end = (
            datetime(year + 1, 1, 1, tzinfo=dt_timezone.utc)
            if month == 12
            else datetime(year, month + 1, 1, tzinfo=dt_timezone.utc)
        )

        keeps = Keep.objects.filter(
            date_of_memory__gte=start,
            date_of_memory__lt=end,
        )

        circle_slug = request.query_params.get('circle_slug')
        if circle_slug:
            try:
                circle = Circle.objects.get(
                    slug=circle_slug,
                    memberships__user=request.user
                )
            except Circle.DoesNotExist:
                return error_response(
                    'circle_not_found',
                    messages=[create_message('errors.circle_not_found')],
                    status_code=404
                )
            keeps = keeps.filter(circle=circle)
        else:
            keeps = keeps.filter(circle__memberships__user=request.user)

        keeps = keeps.prefetch_related('media_files').order_by('date_of_memory', 'created_at')

        # Presign for a day (instead of the 1h default) so URLs cached in the
        # frontend's localStorage keep working between visits.
        expires_in = 86400

        entries = []
        for keep in keeps:
            photos = [
                media.get_url('thumbnail', expires_in)
                if media.thumbnails_generated
                else media.get_url('original', expires_in)
                for media in keep.media_files.all()
                # Videos count once they have a poster-derived thumbnail; their
                # original is an mp4, so there is no fallback for them.
                if media.media_type == 'photo'
                or (media.media_type == 'video' and media.thumbnails_generated)
            ]
            if not photos:
                continue
            entries.append({
                'keep_id': str(keep.id),
                'datetime': keep.date_of_memory.isoformat(),
                'photos': photos,
            })

        return success_response({
            'month': month_param,
            'circle_slug': circle_slug,
            'entries': entries,
        })
