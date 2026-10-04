# Development Guide

## Prerequisites

- Python 3.12 (use the provided `.venv` by running `pip install -r requirements.txt`)
- Docker + Docker Compose for local services (`redis`, `postgres`, Celery workers, Flower)
- Copy the dev settings template: `cp .env.development.example .env.development`

Start the full stack with:

```bash
docker compose up --build
```

The primary API is served at http://localhost:8100/ and Flower (Celery monitoring) at http://localhost:5656/flower/.

> **Note**: The `web` service automatically runs database migrations and seeds demo data on startup. If you need to reseed manually, run `python manage.py seed_demo_data` after containers are up.

## Google OAuth for Local Development

Follow these steps to exercise Google sign-up and sign-in flows against the local stack:

1. **Create credentials in Google Cloud Console**
   - Visit <https://console.cloud.google.com/> and create/select a project.
   - Under **APIs & Services → OAuth consent screen**, configure an Internal/External consent screen and add the `openid`, `email`, and `profile` scopes.
   - Under **APIs & Services → Credentials**, create an **OAuth client ID** of type *Web application*.
   - Add `http://localhost:3053/auth/google-callback` to **Authorized redirect URIs** (swap in your host or domain if different). **Authorized JavaScript origins** are optional: the browser never calls Google from JavaScript in this flow.
   - Download or copy the generated **Client ID** and **Client secret**.
   - The backend also only accepts redirect URIs listed in `OAUTH_ALLOWED_REDIRECT_URIS` (exact match). With `DEBUG=1` it defaults to `http://localhost:3053/auth/google-callback`, `http://127.0.0.1:3053/auth/google-callback` and `http://localhost:3000/auth/google-callback`; any other origin has to be listed (step 2).

2. **Populate local environment variables**
   - Put the values from Google Cloud in `.env` at the repo root (gitignored). `.env.development` doesn't work for these: `docker-compose.yml` sets them in the `web` service's `environment:` block, which overrides `env_file:`.

     ```dotenv
     GOOGLE_OAUTH_CLIENT_ID=your-real-client-id.apps.googleusercontent.com
     GOOGLE_OAUTH_CLIENT_SECRET=your-real-secret
     ```

   - The frontend always sends `<browser origin>/auth/google-callback` as the redirect URI. If you open the app anywhere other than localhost, list that URI in `.env` too (comma-separated, one per origin), and add it to the Google client:

     ```dotenv
     OAUTH_ALLOWED_REDIRECT_URIS=https://app.example.com/auth/google-callback
     ```

3. **Recreate the container**
   - Run `docker compose up -d web` so the Django API picks up the new environment variables. `docker compose restart` keeps the old environment.

Once configured, the login and signup pages will render the Google OAuth button and you can complete the flow end-to-end against your local stack.

## Serving the Stack on Your Own Domain

By default everything is reached at `http://localhost:<port>`. To put the app behind your own hostname (e.g. an HTTPS reverse proxy at `https://app.example.com`), set the URL-related variables in a **`.env` file at the repo root**. It's gitignored, so each machine keeps its own URLs.

> **Why `.env` and not `.env.development`?** The variables below are set in the `environment:` block of `docker-compose.yml` (`${VAR:-default}`), and `environment:` wins over `env_file:`. So values for these keys in `.env.development` are ignored. Compose reads `.env` automatically to fill in those `${VAR}` placeholders.

| Variable | Purpose | Default |
| --- | --- | --- |
| `ACCOUNT_FRONTEND_BASE_URL` | Base URL used in links inside emails (password reset, magic login, email verification, circle invites). | `http://localhost:3053` |
| `DJANGO_ALLOWED_HOSTS` | Hostnames Django accepts. Include your domain and any LAN IP you browse by. | `localhost,127.0.0.1,[::1],web,localhost` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Origins (with scheme) allowed to make CSRF-protected requests. | `http://localhost:3053,http://localhost:3053,http://127.0.0.1:3053` |
| `OAUTH_ALLOWED_REDIRECT_URIS` | Comma-separated redirect URIs Google sign-in accepts, `<origin>/auth/google-callback` for each origin. | localhost:3053 / 127.0.0.1:3053 / localhost:3000 |
| `VITE_ALLOWED_HOSTS` | Comma-separated hostnames the Vite dev server answers to (it always allows localhost and bare IPs). Without your domain here, Vite rejects requests through the proxy. | Empty |
| `MINIO_PUBLIC_ENDPOINT` | Base URL browsers load photos/videos from. Presigned media URLs are signed for this host. The backend itself talks to MinIO via `MINIO_ENDPOINT` (`http://minio:9000`). | `http://localhost:9220` |
| `DASHY_CONFIG` | Path to the Dashy config to mount, so you can keep a copy with your own links. | `./dashy-config.yml` |

Example `.env`:

```dotenv
ACCOUNT_FRONTEND_BASE_URL=https://app.example.com
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,[::1],web,192.168.1.10,app.example.com
DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:3053,http://127.0.0.1:3053,https://app.example.com
MINIO_PUBLIC_ENDPOINT=https://media.example.com
OAUTH_ALLOWED_REDIRECT_URIS=https://app.example.com/auth/google-callback
VITE_ALLOWED_HOSTS=app.example.com
# cp dashy-config.yml volumes/dashy/conf.yml, then edit the links there (volumes/ is gitignored)
DASHY_CONFIG=./volumes/dashy/conf.yml
```

**Media needs its own HTTPS hostname.** MinIO only speaks plain HTTP, and browsers (iOS Safari in particular) won't load `http://` images on an `https://` page, so photos show up blank. Put MinIO (host port `9220`) behind your reverse proxy on a separate hostname and point `MINIO_PUBLIC_ENDPOINT` at it. The proxy **must pass the `Host` header through unchanged**, because it's part of the presigned-URL signature. Browsers only need `GET`/`HEAD`, since uploads go from the backend to MinIO directly.

**Reverse-proxy routing for the app hostname:** send `/api/`, `/admin/`, `/static/`, `/media/` and `/health/` to Django (host port `8100`). Send everything else, including the Vite HMR websocket, to the Vite dev server (host port `3053`).

**Apply changes** by recreating the containers. `docker compose restart` keeps the old environment, so use:

```bash
docker compose up -d web celery-worker-1 celery-beat   # add `dashy` if you changed DASHY_CONFIG, `web-frontend` if you changed VITE_ALLOWED_HOSTS
```

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

Circle invitation flows rely on a handful of environment variables to control rate limiting, onboarding TTLs, and reminder cadences. The defaults are defined in `mysite/config/settings/auth.py`, but for local debugging you can adjust the following values inside `.env.development` before restarting Docker:

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

After updating these values run `docker compose up -d web celery-worker-1 celery-beat` so the API and Celery tasks pick up the new settings. A plain `docker compose restart` doesn't reload `.env.development`.

Feel free to extend the demo data to cover new features—just update the seeding command and this document accordingly.
