# Development Guide

## Prerequisites

- Python 3.12 (use the provided `.venv` by running `pip install -r requirements.txt`)
- Docker + Docker Compose for local services (`redis`, `postgres`, Celery workers, Flower)

Start the full stack with:

```bash
docker compose up --build
```

The primary API is served at http://localhost:8000/ and Flower (Celery monitoring) at http://localhost:5556/flower.

> **Note**: The `web` service automatically runs database migrations and seeds demo data on startup. If you need to reseed manually, run `python manage.py seed_demo_data` after containers are up.

## Google OAuth for Local Development

Follow these steps to exercise Google sign-up and sign-in flows against the local stack:

1. **Create credentials in Google Cloud Console**
   - Visit <https://console.cloud.google.com/> and create/select a project.
   - Under **APIs & Services → OAuth consent screen**, configure an Internal/External consent screen and add the `openid`, `email`, and `profile` scopes.
   - Under **APIs & Services → Credentials**, create an **OAuth client ID** of type *Web application*.
   - Add `http://192.168.1.76:3053` to **Authorized JavaScript origins** and `http://192.168.1.76:3053/auth/google/callback` to **Authorized redirect URIs** (swap in your host IP if different).
   - Download or copy the generated **Client ID** and **Client secret**.

2. **Populate local environment variables**
   - Update `.env.development` with the values from Google Cloud (Compose loads this file automatically).

     ```dotenv
     GOOGLE_OAUTH_CLIENT_ID=your-real-client-id.apps.googleusercontent.com
     GOOGLE_OAUTH_CLIENT_SECRET=your-real-secret
     GOOGLE_OAUTH_REDIRECT_URI=http://192.168.1.76:3053/auth/google/callback
     ```

   - If you use a standalone frontend (outside Docker), mirror the redirect URI (and host IP) in `web/.env.local`.

3. **Restart the containers**
   - Run `docker compose up --build` (or `docker compose restart web web-frontend`) so the Django API picks up the new environment variables.

Once configured, the login and signup pages will render the Google OAuth button and you can complete the flow end-to-end against your local stack.

## Seeding Demo Data

Demo accounts are created automatically when the `web` container starts (or you can rerun `python manage.py seed_demo_data`). The dataset includes:

| Account / Object            | Username            | Email                      | Notes |
|-----------------------------|---------------------|----------------------------|-------|
| Superuser                   | `superadmin`        | superadmin@example.com     | Full admin access |
| Guardian circle admin       | `guardian_admin`    | guardian@example.com       | Owns "Guardian Family" circle |
| Family member               | `family_member`     | member@example.com         | Member of Guardian Family |
| Teen member (linked child)  | `teen_member`       | teen@example.com           | Linked to child profile "Avery" |
| Solo user                   | `solo_user`         | solo@example.com           | No circle memberships |
| Secondary circle admin      | `second_admin`      | second@example.com         | Owns "Adventure Club" circle |

All seeded accounts share the password `password123` (update as needed after login).

### Sample Data Overview

- **Guardian Family circle**: includes an admin, two members, three child profiles (linked, pending upgrade, and unlinked), plus a pending invitation.
- **Adventure Club circle**: admin-only circle to test empty-circle flows.
- **Solo user**: demonstrates how APIs behave when a user has not joined any circles yet.
- **Notification preferences**: global defaults plus a sample per-circle override to exercise preference APIs.

## Running Tests

Tests are configured to run without external services like Redis. They use:
- In-memory cache (instead of Redis)
- In-memory email backend (instead of actual email service)
- Synchronous Celery execution (instead of Redis broker)
- SQLite or PostgreSQL for the database

To run tests:

```bash
# Using Django's test runner (automatically uses test_settings)
python manage.py test --settings=mysite.test_settings

# Or using pytest (test_settings configured in pytest.ini)
pytest

# Run specific test files
python manage.py test users.tests.test_models --settings=mysite.test_settings
```

The test settings (`mysite/test_settings.py`) override the production settings to ensure tests run quickly and don't depend on external services.

## Useful Commands

- Lint formatting: `ruff check .`
- Format code: `ruff format .`
- Open Django shell with project context: `python manage.py shell_plus`

## Circle Invitation Configuration

Circle invitation flows rely on a handful of environment variables to control rate limiting, onboarding TTLs, and reminder cadences. The defaults live in `.env.example`, but for local debugging you can adjust the following values inside `.env.development` before restarting Docker:

| Variable | Purpose | Default |
| --- | --- | --- |
| `CIRCLE_INVITE_RATELIMIT` | Per-admin rate limit enforced by `django-ratelimit` (format `<count>/<window>`). | `10/15m` |
| `CIRCLE_INVITE_RESEND_RATELIMIT` | Rate limit for manual resend requests (format `<count>/<window>`). | `5/15m` |
| `CIRCLE_INVITE_CIRCLE_LIMIT` | Maximum invitations a circle can send within the configured window. | `25` |
| `CIRCLE_INVITE_CIRCLE_LIMIT_WINDOW_MINUTES` | Window (in minutes) for the per-circle limit. | `60` |
| `CIRCLE_INVITE_REMINDER_DELAY_MINUTES` | Minutes to wait before sending the first reminder email. | `1440` |
| `CIRCLE_INVITE_REMINDER_COOLDOWN_MINUTES` | Minimum minutes between reminder emails for the same invite. | `1440` |
| `CIRCLE_INVITE_REMINDER_BATCH_SIZE` | Batch size for the reminder Celery task. | `100` |
| `CIRCLE_INVITE_ONBOARDING_TTL_MINUTES` | TTL for onboarding tokens issued to invitees. | `60` |

After updating these values run `docker compose restart web` so the API and Celery tasks pick up the new settings.

Feel free to extend the demo data to cover new features—just update the seeding command and this document accordingly.
