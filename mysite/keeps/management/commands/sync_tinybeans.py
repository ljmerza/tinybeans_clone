"""Sync a real Tinybeans account into this app.

Logs into the (unofficial) Tinybeans API, walks every followed journal, and
imports entries (photos, videos, notes), their comments and reactions, plus
journals (as circles) and children (as child profiles).

Idempotent: every imported remote object is tracked in TinybeansImportRecord
keyed by its Tinybeans id, so re-running the command never duplicates data.
Deleting an imported object locally also deletes its tracking row, which means
the next sync run will re-import it.

Examples:
    # Full sync of everything the account can see
    python manage.py sync_tinybeans --email you@example.com

    # Only entries whose Tinybeans timestamp falls in a date range (UTC, inclusive)
    python manage.py sync_tinybeans --email you@example.com \
        --start 2023-01-01 --end 2023-12-31

    # Preview without writing anything
    python manage.py sync_tinybeans --email you@example.com --dry-run

Credentials can also come from the TINYBEANS_EMAIL / TINYBEANS_PASSWORD
(or TINYBEANS_ACCESS_TOKEN) environment variables.
"""
import getpass
import mimetypes
import os
import time
from datetime import datetime, timedelta, timezone as dt_timezone
from urllib.parse import urlparse

import requests
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from mysite.circles.models import Circle, CircleMembership
from mysite.keeps.models import (
    Keep,
    KeepComment,
    KeepMedia,
    KeepReaction,
    KeepType,
    TinybeansImportRecord,
    TinybeansObjectType,
)
from mysite.keeps.storage import get_storage_backend
from mysite.keeps.tasks import generate_image_sizes
from mysite.users.models.child_profile import ChildProfile
from mysite.users.models.user import User, UserRole

API_BASE = 'https://tinybeans.com/api/1'
# Public client id used by the Tinybeans web app (same one the pytinybeans
# project uses); required by the API on every request.
CLIENT_ID = '13bcd503-2137-9085-a437-d9f2ac9281a1'
PAGE_SIZE = 200
# Preferred blob (image rendition) keys, best quality first.
BLOB_PREFERENCE = ('o2', 'o', 'xl', 'l', 'm', 's2', 's', 't', 'p')
# Tinybeans emotion labels -> KeepReaction types. Unknown labels fall back to 'like'.
REACTION_MAP = {
    'love': 'love',
    'like': 'like',
    'laugh': 'laugh',
    'haha': 'laugh',
    'funny': 'laugh',
    'wow': 'wow',
    'celebrate': 'celebrate',
    'yay': 'celebrate',
}
PLACEHOLDER_EMAIL_DOMAIN = 'tinybeans-import.invalid'


class TinybeansApiError(Exception):
    """Raised when the Tinybeans API returns an unusable response."""


class TinybeansClient:
    """Minimal client for the unofficial Tinybeans REST API."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers['user-agent'] = 'tinybeans-copy-sync/1.0'

    def login(self, username: str, password: str) -> dict:
        """Authenticate and store the access token. Returns the remote user dict."""
        response = self._request('POST', 'authenticate', json={
            'username': username,
            'password': password,
            'clientId': CLIENT_ID,
        })
        data = response.json()
        token = data.get('accessToken')
        if not token:
            raise TinybeansApiError(f'Login failed: {data}')
        self.set_token(token)
        return data.get('user') or {}

    def set_token(self, token: str):
        self.session.headers['authorization'] = token

    def followings(self) -> list:
        """List followed journals (includes the account's own journals)."""
        response = self._request('GET', 'followings', params={'clientId': CLIENT_ID})
        return response.json().get('followings') or []

    def entries_page(self, journal_id, last_ms: int) -> dict:
        """One page of journal entries older than ``last_ms`` (newest first)."""
        response = self._request(
            'GET',
            f'journals/{journal_id}/entries',
            params={'clientId': CLIENT_ID, 'fetchSize': PAGE_SIZE, 'last': int(last_ms)},
        )
        return response.json()

    def iter_entries(self, journal_id, start_ms=None, end_ms=None):
        """Yield entries newest-to-oldest, stopping once past ``start_ms``.

        Callers must still filter each entry by exact timestamp; page
        boundaries are only used to stop paginating early.
        """
        last = end_ms
        if last is None:
            last = int(time.time() * 1000) + 24 * 3600 * 1000
        while True:
            data = self.entries_page(journal_id, last)
            entries = data.get('entries') or []
            if not entries:
                return
            yield from entries
            timestamps = [e['timestamp'] for e in entries if e.get('timestamp')]
            if not timestamps:
                return
            page_min = min(timestamps)
            remaining = data.get('numEntriesRemaining') or 0
            if remaining <= 0:
                return
            if page_min >= last:  # no progress; avoid an infinite loop
                return
            if start_ms is not None and page_min < start_ms:
                return
            last = page_min

    def download(self, url: str) -> tuple:
        """Download a media file. Returns (content_bytes, content_type)."""
        for attempt in range(3):
            try:
                response = self.session.get(url, timeout=(10, 300))
                response.raise_for_status()
                content_type = (response.headers.get('content-type') or '').split(';')[0].strip()
                return response.content, content_type or 'application/octet-stream'
            except requests.RequestException:
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)

    def _request(self, method, path, **kwargs):
        for attempt in range(3):
            try:
                response = self.session.request(method, f'{API_BASE}/{path}', timeout=(10, 60), **kwargs)
                if response.status_code in (401, 403):
                    raise TinybeansApiError(
                        f'Tinybeans API rejected the request ({response.status_code}): {response.text[:300]}'
                    )
                response.raise_for_status()
                return response
            except requests.RequestException:
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)


class Command(BaseCommand):
    help = 'Sync journals, entries, media, comments and reactions from a real Tinybeans account.'

    def add_arguments(self, parser):
        parser.add_argument('--email', default=os.environ.get('TINYBEANS_EMAIL'),
                            help='Tinybeans account email (or TINYBEANS_EMAIL env var)')
        parser.add_argument('--password', default=os.environ.get('TINYBEANS_PASSWORD'),
                            help='Tinybeans account password (or TINYBEANS_PASSWORD env var; prompted if omitted)')
        parser.add_argument('--token', default=os.environ.get('TINYBEANS_ACCESS_TOKEN'),
                            help='Existing Tinybeans access token instead of email/password '
                                 '(requires --owner)')
        parser.add_argument('--start', help='Only sync entries on/after this date (YYYY-MM-DD, UTC)')
        parser.add_argument('--end', help='Only sync entries on/before this date (YYYY-MM-DD, UTC)')
        parser.add_argument('--journal', action='append', type=str, default=None,
                            help='Only sync this Tinybeans journal id (repeatable)')
        parser.add_argument('--owner', help='Email of the local user who owns imported circles '
                                            '(default: the Tinybeans account email)')
        parser.add_argument('--limit', type=int, default=None,
                            help='Stop after importing this many new entries (for testing)')
        parser.add_argument('--dry-run', action='store_true',
                            help='Report what would be imported without writing anything')
        parser.add_argument('--sync-thumbnails', action='store_true',
                            help='Generate photo thumbnails inline instead of queueing Celery tasks')

    def handle(self, *args, **options):
        self.dry = options['dry_run']
        self.sync_thumbnails = options['sync_thumbnails']
        self.limit = options['limit']
        self.counts = {
            'circles': 0, 'children': 0, 'users': 0, 'entries': 0, 'media': 0,
            'comments': 0, 'reactions': 0, 'entries_skipped': 0, 'errors': 0,
        }
        self.storage = None if self.dry else get_storage_backend()

        start_ms, end_ms, start_dt, end_dt = self._parse_range(options)
        self.client = TinybeansClient()
        login_user = self._authenticate(options)
        self.owner = self._resolve_owner(options, login_user)
        self._link_remote_user(login_user, self.owner)

        journals = self._select_journals(options)
        if not journals:
            raise CommandError('No Tinybeans journals found for this account (check --journal ids).')

        if self.dry:
            self.stdout.write(self.style.WARNING('DRY RUN — nothing will be written.'))
        if start_dt or end_dt:
            self.stdout.write(
                f"Date range: {start_dt.date() if start_dt else 'beginning'} .. "
                f"{end_dt.date() if end_dt else 'now'} (UTC, inclusive)"
            )

        try:
            for journal in journals:
                self._sync_journal(journal, start_ms, end_ms)
        except _LimitReached:
            self.stdout.write(self.style.WARNING(f'Stopped after --limit {self.limit} new entries.'))

        c = self.counts
        verb = 'would create' if self.dry else 'created'
        self.stdout.write(self.style.SUCCESS(
            f"Done. Circles {verb}: {c['circles']}, children: {c['children']}, "
            f"users: {c['users']}, entries: {c['entries']} (media files: {c['media']}), "
            f"comments: {c['comments']}, reactions: {c['reactions']}. "
            f"Entries already synced: {c['entries_skipped']}. Errors: {c['errors']}."
        ))
        if c['errors']:
            self.stdout.write(self.style.WARNING(
                'Some entries failed (see warnings above); re-run the command to retry them.'
            ))

    # ------------------------------------------------------------------ setup

    def _parse_range(self, options):
        start_dt = end_dt = None
        start_ms = end_ms = None
        if options['start']:
            start_dt = self._parse_date(options['start'], '--start')
            start_ms = int(start_dt.timestamp() * 1000)
        if options['end']:
            end_dt = self._parse_date(options['end'], '--end')
            # inclusive: page/filter up to the end of that day
            end_ms = int((end_dt + timedelta(days=1)).timestamp() * 1000) - 1
        if start_ms and end_ms and start_ms > end_ms:
            raise CommandError('--start must be on or before --end.')
        return start_ms, end_ms, start_dt, end_dt

    @staticmethod
    def _parse_date(value, flag):
        try:
            return datetime.strptime(value, '%Y-%m-%d').replace(tzinfo=dt_timezone.utc)
        except ValueError:
            raise CommandError(f'{flag} must be YYYY-MM-DD, got {value!r}')

    def _authenticate(self, options):
        if options['token']:
            self.client.set_token(options['token'])
            if not options['owner']:
                raise CommandError('--owner is required when authenticating with --token.')
            return {}
        email = options['email']
        if not email:
            raise CommandError('Provide --email (or TINYBEANS_EMAIL), or use --token.')
        password = options['password'] or getpass.getpass('Tinybeans password: ')
        self.stdout.write(f'Logging into Tinybeans as {email}...')
        try:
            user = self.client.login(email, password)
        except (requests.RequestException, TinybeansApiError) as exc:
            raise CommandError(f'Tinybeans login failed: {exc}')
        return user

    def _resolve_owner(self, options, login_user):
        email = options['owner'] or login_user.get('emailAddress') or options['email']
        if not email:
            raise CommandError('Could not determine the local owner account; pass --owner.')
        user = User.objects.filter(email__iexact=email).first()
        if user:
            return user
        if self.dry:
            self.stdout.write(f'Would create local owner account {email}')
            self.counts['users'] += 1
            return User(email=email)  # unsaved stand-in, never persisted in dry mode
        user = User(
            email=email.lower(),
            first_name=login_user.get('firstName') or '',
            last_name=login_user.get('lastName') or '',
            role=UserRole.CIRCLE_ADMIN,
        )
        user.set_unusable_password()
        user.save()
        self.counts['users'] += 1
        self.stdout.write(self.style.WARNING(
            f'Created local owner account {user.email} with no password '
            f'(use password reset to enable login).'
        ))
        return user

    def _link_remote_user(self, login_user, owner):
        """Map the Tinybeans login user's id to the local owner account."""
        remote_id = (login_user or {}).get('id')
        if remote_id is None or self.dry:
            return
        if not self._record(TinybeansObjectType.USER, remote_id):
            self._save_record(
                TinybeansObjectType.USER, remote_id, user=owner,
                payload={'emailAddress': login_user.get('emailAddress')},
            )

    def _select_journals(self, options):
        try:
            followings = self.client.followings()
        except (requests.RequestException, TinybeansApiError) as exc:
            raise CommandError(f'Could not list Tinybeans journals: {exc}')
        journals = [f.get('journal') for f in followings if f.get('journal')]
        if options['journal']:
            wanted = {str(j) for j in options['journal']}
            journals = [j for j in journals if str(j.get('id')) in wanted]
        return journals

    # ------------------------------------------------------------ journal sync

    def _sync_journal(self, journal, start_ms, end_ms):
        title = journal.get('title') or f"Tinybeans journal {journal.get('id')}"
        self.stdout.write(f"Syncing journal '{title}' (id {journal.get('id')})...")
        circle = self._ensure_circle(journal, title)
        for child in journal.get('children') or []:
            self._ensure_child(child, circle)

        processed = 0
        for entry in self.client.iter_entries(journal['id'], start_ms, end_ms):
            ts_ms = entry.get('timestamp')
            if ts_ms is None:
                continue
            if (start_ms is not None and ts_ms < start_ms) or (end_ms is not None and ts_ms > end_ms):
                continue
            try:
                self._import_entry(entry, circle)
            except _LimitReached:
                raise
            except Exception as exc:  # keep going; the entry can be retried on the next run
                self.counts['errors'] += 1
                self.stderr.write(self.style.WARNING(
                    f"Failed to import entry {entry.get('id')}: {exc}"
                ))
            processed += 1
            if processed % 100 == 0:
                self.stdout.write(f'  ...{processed} entries examined')
        self.stdout.write(f'  {processed} entries examined in range.')

    def _ensure_circle(self, journal, title):
        record = self._record(TinybeansObjectType.JOURNAL, journal['id'])
        if record:
            return record.circle
        self.counts['circles'] += 1
        if self.dry:
            self.stdout.write(f"  Would create circle '{title}'")
            return None
        circle = Circle.objects.create(name=title[:255], created_by=self.owner)
        CircleMembership.objects.get_or_create(
            user=self.owner, circle=circle,
            defaults={'role': UserRole.CIRCLE_ADMIN, 'is_owner': True},
        )
        self._save_record(
            TinybeansObjectType.JOURNAL, journal['id'], circle=circle,
            payload={'title': title},
        )
        return circle

    def _ensure_child(self, child, circle):
        child_id = child.get('id')
        if child_id is None or self._record(TinybeansObjectType.CHILD, child_id):
            return
        name = ' '.join(filter(None, [child.get('firstName'), child.get('lastName')])) or 'Child'
        self.counts['children'] += 1
        if self.dry:
            self.stdout.write(f'  Would create child profile {name}')
            return
        birthdate = None
        if child.get('dob'):
            try:
                birthdate = datetime.strptime(child['dob'], '%Y-%m-%d').date()
            except ValueError:
                pass
        profile = ChildProfile.objects.create(
            circle=circle, display_name=name[:150], birthdate=birthdate,
        )
        self._save_record(
            TinybeansObjectType.CHILD, child_id, child=profile,
            payload={'firstName': child.get('firstName'), 'dob': child.get('dob')},
        )

    def _ensure_user(self, remote_user, circle):
        """Map a Tinybeans user (from a comment/emotion) to a local user."""
        remote_id = remote_user.get('id')
        if remote_id is None:
            return self.owner
        record = self._record(TinybeansObjectType.USER, remote_id)
        if record:
            user = record.user
        else:
            email = (remote_user.get('emailAddress') or '').strip().lower() \
                or f'tinybeans-{remote_id}@{PLACEHOLDER_EMAIL_DOMAIN}'
            user = User.objects.filter(email__iexact=email).first()
            if not user:
                self.counts['users'] += 1
                if self.dry:
                    return self.owner
                user = User(
                    email=email,
                    first_name=remote_user.get('firstName') or '',
                    last_name=remote_user.get('lastName') or '',
                    is_active=False,  # imported placeholder; cannot log in
                )
                user.set_unusable_password()
                user.save()
            if not self.dry:
                self._save_record(
                    TinybeansObjectType.USER, remote_id, user=user,
                    payload={k: remote_user.get(k)
                             for k in ('emailAddress', 'firstName', 'lastName', 'username')},
                )
        if circle is not None and not self.dry:
            CircleMembership.objects.get_or_create(
                user=user, circle=circle,
                defaults={'role': UserRole.CIRCLE_MEMBER, 'invited_by': self.owner},
            )
        return user

    # -------------------------------------------------------------- entry sync

    def _import_entry(self, entry, circle):
        entry_id = entry.get('id') or entry.get('uuid')
        if entry_id is None:
            return
        ts = datetime.fromtimestamp(entry['timestamp'] / 1000, tz=dt_timezone.utc)
        record = self._record(TinybeansObjectType.ENTRY, entry_id)
        if record:
            self.counts['entries_skipped'] += 1
            keep = record.keep
        else:
            keep = self._create_keep(entry, circle, ts, entry_id)
        # Comments/reactions are keyed by their own Tinybeans ids, so new ones
        # attached to an already-synced entry are still picked up.
        self._sync_comments(entry, keep, circle, ts)
        self._sync_emotions(entry, keep, circle, ts)

    def _create_keep(self, entry, circle, ts, entry_id):
        self.counts['entries'] += 1
        if self.limit is not None and self.counts['entries'] > self.limit:
            self.counts['entries'] -= 1
            raise _LimitReached()

        is_video = entry.get('attachmentType') == 'VIDEO' and entry.get('attachmentUrl_mp4')
        blobs = entry.get('blobs') or {}
        blob_url = next((blobs[k] for k in BLOB_PREFERENCE if blobs.get(k)), None)
        has_media = bool(is_video or blob_url)

        if self.dry:
            kind = 'video' if is_video else ('photo' if blob_url else 'note')
            self.counts['media'] += 1 if has_media else 0
            self.stdout.write(f"  Would import {kind} entry {entry_id} from {ts.date()}")
            return None

        # Download + store media BEFORE opening the DB transaction.
        media_specs = []  # (storage_key, filename, content_type, media_type, size)
        if is_video:
            media_specs.append(self._fetch_media(entry['attachmentUrl_mp4'], entry_id, 'video'))
        elif blob_url:
            media_specs.append(self._fetch_media(blob_url, entry_id, 'photo'))

        with transaction.atomic():
            keep = Keep.objects.create(
                circle=circle,
                created_by=self._entry_author(entry),
                keep_type=KeepType.MEDIA if has_media else KeepType.NOTE,
                description=entry.get('caption') or '',
                date_of_memory=ts,
                created_at=ts,
            )
            photo_media_ids = []
            for order, (key, filename, content_type, media_type, size) in enumerate(media_specs):
                media = KeepMedia.objects.create(
                    keep=keep,
                    media_type=media_type,
                    upload_order=order,
                    storage_key_original=key,
                    file_size=size,
                    original_filename=filename,
                    content_type=content_type,
                )
                self.counts['media'] += 1
                if media_type == 'photo':
                    photo_media_ids.append(media.id)
            self._save_record(
                TinybeansObjectType.ENTRY, entry_id, keep=keep,
                payload={'type': entry.get('type'), 'timestamp': entry.get('timestamp'),
                         'journalId': entry.get('journalId')},
            )

        for media_id in photo_media_ids:
            self._generate_thumbnails(media_id)
        return keep

    def _entry_author(self, entry):
        author_id = entry.get('userId')
        if author_id is not None:
            record = self._record(TinybeansObjectType.USER, author_id)
            if record and record.user:
                return record.user
        return self.owner

    def _fetch_media(self, url, entry_id, media_type):
        content, content_type = self.client.download(url)
        filename = os.path.basename(urlparse(url).path) or f'tinybeans-{entry_id}'
        if '.' not in filename:
            filename += mimetypes.guess_extension(content_type) or ''
        storage_key = self.storage.save(
            file_content=content, filename=filename, content_type=content_type,
        )
        return storage_key, filename[:255], content_type, media_type, len(content)

    def _generate_thumbnails(self, media_id):
        try:
            if self.sync_thumbnails:
                generate_image_sizes.apply(args=[media_id])
            else:
                generate_image_sizes.delay(media_id)
        except Exception as exc:
            self.stderr.write(self.style.WARNING(
                f'Thumbnail generation for media {media_id} could not be started: {exc}'
            ))

    def _sync_comments(self, entry, keep, circle, ts):
        for comment in entry.get('comments') or []:
            comment_id = comment.get('id')
            if comment_id is None or self._record(TinybeansObjectType.COMMENT, comment_id):
                continue
            self.counts['comments'] += 1
            if self.dry or keep is None:
                continue
            user = self._ensure_user(comment.get('user') or {}, circle)
            created_at = ts
            if comment.get('timestamp'):
                created_at = datetime.fromtimestamp(comment['timestamp'] / 1000, tz=dt_timezone.utc)
            with transaction.atomic():
                obj = KeepComment.objects.create(
                    keep=keep, user=user,
                    comment=comment.get('details') or '',
                    created_at=created_at,
                )
                self._save_record(
                    TinybeansObjectType.COMMENT, comment_id, comment=obj,
                    payload={'entryId': entry.get('id')},
                )

    def _sync_emotions(self, entry, keep, circle, ts):
        for emotion in entry.get('emotions') or []:
            emotion_id = emotion.get('id')
            if emotion_id is None or self._record(TinybeansObjectType.EMOTION, emotion_id):
                continue
            self.counts['reactions'] += 1
            if self.dry or keep is None:
                continue
            user = self._ensure_user({'id': emotion.get('userId')}, circle)
            emotion_type = emotion.get('type')
            label = emotion_type.get('label') if isinstance(emotion_type, dict) else emotion_type
            reaction_type = REACTION_MAP.get((label or '').lower(), 'like')
            created_at = ts
            if emotion.get('timestamp'):
                created_at = datetime.fromtimestamp(emotion['timestamp'] / 1000, tz=dt_timezone.utc)
            with transaction.atomic():
                obj, _ = KeepReaction.objects.get_or_create(
                    keep=keep, user=user,
                    defaults={'reaction_type': reaction_type, 'created_at': created_at},
                )
                self._save_record(
                    TinybeansObjectType.EMOTION, emotion_id, reaction=obj,
                    payload={'entryId': entry.get('id'), 'label': label},
                )

    # ------------------------------------------------------------------ records

    @staticmethod
    def _record(object_type, tinybeans_id):
        return TinybeansImportRecord.objects.filter(
            object_type=object_type, tinybeans_id=str(tinybeans_id),
        ).first()

    def _save_record(self, object_type, tinybeans_id, payload=None, **links):
        return TinybeansImportRecord.objects.create(
            object_type=object_type,
            tinybeans_id=str(tinybeans_id),
            payload=payload or {},
            **links,
        )


class _LimitReached(Exception):
    """Internal: raised to stop the sync once --limit new entries were imported."""
