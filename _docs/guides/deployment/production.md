# Production deployment

Production runs the CI-built image (`Dockerfile` target `production`: nginx and gunicorn under
supervisord) from `docker-compose.prod.yml`, next to Celery, Redis and MinIO. Postgres is an
existing server that the stack reaches over an external Docker network. A TLS-terminating reverse
proxy (and optionally Cloudflare) sits in front of the published web and MinIO ports.

Placeholders look like `<this>`. Nothing secret or host-specific belongs in the repository: keep
the env files outside the checkout with mode `0600`.

## What runs

| Service | What it does | Host port |
|---|---|---|
| `circles-web` | nginx serves the SPA and `/static/`, and proxies `/api/`, `/admin/`, `/health/` and `/metrics` to gunicorn. No migrations on start (`RUN_MIGRATIONS=0`). | `${CIRCLES_WEB_PORT:-8110}` |
| `circles-worker` | `celery worker --concurrency 4`. It consumes every queue in `CELERY_TASK_QUEUES` (email, sms, media, maintenance). | none |
| `circles-beat` | Celery beat. Schedule file in `${CIRCLES_DATA_DIR}/beat`. | none |
| `circles-flower` | Celery dashboard, for the LAN only. Give it no public vhost. | `${CIRCLES_FLOWER_PORT:-5657}` |
| `circles-redis` | Redis 7.4 with AOF. Celery broker and results, cache, rate limits. | none |
| `circles-minio` | MinIO, which stores the media. The S3 API is for the media reverse proxy; the console listens on loopback only. | `${CIRCLES_MINIO_PORT:-9230}`, `127.0.0.1:${CIRCLES_MINIO_CONSOLE_PORT:-9231}` |
| `circles-minio-init` | One-shot (profile `init`). Creates the bucket and leaves it private. | none |
| `circles-pg-backup` | Nightly `pg_dump -Fc`, keeping 14 days. | none |

Networks: `circles_backend` has a fixed name so other projects can join it. The external
`${CIRCLES_DB_NETWORK:-docker_db_network}` holds the Postgres server, reachable as `postgres`. Every
service name starts with `circles-`, so none of them shadow `postgres` on that shared network.

## Compose variables

Set these in the shell or in a small compose env file that you pass with `--env-file`. They are
not app settings.

| Variable | Required | Example / default |
|---|---|---|
| `CIRCLES_IMAGE` | yes | `ghcr.io/ljmerza/circles:<release tag>` |
| `CIRCLES_ENV_FILE` | yes | `<path>/circles.env` (app settings below) |
| `CIRCLES_MINIO_ENV_FILE` | yes | `<path>/circles-minio.env` (MinIO root credentials only) |
| `CIRCLES_DATA_DIR` | yes | `<path>/circles` (contains `minio/`, `redis/`, `upload-tmp/`, `beat/`, `backups/postgres/`) |
| `CIRCLES_DB_NETWORK` | no | `docker_db_network` |
| `CIRCLES_TZ` | no | `UTC`. Timezone for the 03:30 backup. |
| `CIRCLES_WEB_PORT`, `CIRCLES_FLOWER_PORT`, `CIRCLES_MINIO_PORT`, `CIRCLES_MINIO_CONSOLE_PORT` | no | `8110`, `5657`, `9230`, `9231` |
| `CIRCLES_BACKEND_NETWORK` | no | `circles_backend` |
| `CIRCLES_BUCKET` | no | `circles-media`. Bucket that `circles-minio-init` creates. Must match `MINIO_BUCKET_NAME`. |
| `CIRCLES_MINIO_IMAGE`, `CIRCLES_MC_IMAGE` | no | Digest-pinned `minio/minio` and `minio/mc` (see [MinIO image availability](#minio-image-availability)). |

MinIO gets its own env file on purpose. MinIO reads `MINIO_ACCESS_KEY`/`MINIO_SECRET_KEY` (the app
user's credentials) as legacy root credentials, so it must never load the app env file.

`<path>/circles-minio.env`:

```
MINIO_ROOT_USER=<openssl rand -hex 32>
MINIO_ROOT_PASSWORD=<openssl rand -hex 32>
```

## App env file (`CIRCLES_ENV_FILE`)

Generate every secret fresh; never reuse dev values. Avoid `$` in values, because compose
interpolates it.

### Secrets

| Variable | How to make it |
|---|---|
| `DJANGO_SECRET_KEY` | `python3 -c 'import secrets;print(secrets.token_urlsafe(64))'`. A new key logs everyone out and voids magic links and trusted devices. |
| `TWOFA_ENCRYPTION_KEY` | `python3 -c 'from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())'`. **Back it up**: losing it loses every 2FA secret. |
| `POSTGRES_PASSWORD` | `openssl rand -hex 32`. Set it on the role with `\password circles`. |
| `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` | The bucket-scoped app user (see below): `openssl rand -hex 10` / `openssl rand -hex 32`. Not the root credentials. |
| `METRICS_TOKEN` | `openssl rand -hex 32`. Prometheus sends it as `Authorization: Bearer <token>`. Empty disables `/metrics` (404). |
| `MAILJET_API_KEY` / `MAILJET_API_SECRET` | Mailjet dashboard. Mailjet is used only when both are set; otherwise mail goes to `EMAIL_BACKEND`. |
| `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET` | Google Cloud console, Web OAuth client. Only if Google sign-in is wanted. |
| `FLOWER_BASIC_AUTH` | `<user>:<password>`. Flower reads it itself; without it Flower has no login. |

### Settings

```
# Django
DJANGO_DEBUG=0
DJANGO_SECRET_KEY=<secret>
DJANGO_ALLOWED_HOSTS=<app host>,<LAN host or IP Prometheus scrapes>,localhost,127.0.0.1
DJANGO_CSRF_TRUSTED_ORIGINS=https://<app host>
ACCOUNT_FRONTEND_BASE_URL=https://<app host>
FRONTEND_BASE_URL=https://<app host>
# Start HSTS short and narrow; raise it once HTTPS is proven.
DJANGO_SECURE_HSTS_SECONDS=3600
DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=0
DJANGO_SECURE_HSTS_PRELOAD=0

# Client IP: gunicorn only hears from the image's own nginx, which resolves the
# visitor (realip) and passes one address on.
DJANGO_TRUST_FORWARDED_FOR=1
DJANGO_TRUSTED_PROXY_IPS=127.0.0.1,::1
RATELIMIT_ENABLE=1
# Do NOT copy the dev compose values TWOFA_RATE_LIMIT_MAX=0, TWOFA_RATE_LIMIT_WINDOW=0
# or TWOFA_LOCKOUT_ENABLED=0. Leave them unset for the real defaults.

# 2FA
TWOFA_ENCRYPTION_KEY=<fernet key>
TWOFA_ISSUER_NAME=Circles

# Postgres (shared server, database and role "circles")
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=circles
POSTGRES_USER=circles
POSTGRES_PASSWORD=<secret>
# The default is "require"; set disable if the server has no TLS.
POSTGRES_SSL_MODE=disable
POSTGRES_CONN_MAX_AGE=60

# Redis / Celery
REDIS_URL=redis://circles-redis:6379/0
CELERY_BROKER_URL=redis://circles-redis:6379/0
CELERY_RESULT_BACKEND=redis://circles-redis:6379/0
CELERY_TIMEZONE=<IANA zone, e.g. America/New_York>

# MinIO (app user, not root). Plain HTTP inside the Docker network.
MINIO_ENDPOINT=http://circles-minio:9000
MINIO_ACCESS_KEY=<app access key>
MINIO_SECRET_KEY=<app secret key>
MINIO_BUCKET_NAME=circles-media
MINIO_USE_SSL=0
DJANGO_ALLOW_INSECURE_MINIO=1
# Browsers load media from here; presigned URLs are signed for this host.
MINIO_PUBLIC_ENDPOINT=https://<media host>

# Uploads: see "Upload size" below. 90 MiB keeps one upload under a 100 MB proxy cap.
MAX_UPLOAD_SIZE=94371840
MAX_VIDEO_UPLOAD_SIZE=94371840

# Mail. Until Mailjet is live, the console backend just logs mail.
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=<verified sender address>
MAILJET_API_KEY=<key>
MAILJET_API_SECRET=<secret>
MAILJET_FROM_EMAIL=<verified sender address>
MAILJET_FROM_NAME=Circles
# Start in sandbox; set 0 once the sender is verified.
MAILJET_USE_SANDBOX=1

# SMS: the default provider is twilio, which isn't set up.
SMS_PROVIDER=console

# Google sign-in (optional). Exact callback URIs, comma-separated.
GOOGLE_OAUTH_CLIENT_ID=<client id>.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=<client secret>
OAUTH_ALLOWED_REDIRECT_URIS=https://<app host>/auth/google-callback

# Monitoring and Flower
METRICS_TOKEN=<secret>
FLOWER_BASIC_AUTH=<user>:<password>
```

The compose file sets `UPLOAD_TEMP_DIR=/upload-tmp` (shared by web and worker) and `RUN_MIGRATIONS=0`
on web itself. The image sets `DJANGO_SETTINGS_MODULE=mysite.config.settings.production`. Every
other knob is in [env_reference.md](../security/env_reference.md).

In the Google console the redirect URI is `https://<app host>/auth/google-callback`, exactly as
written: a hyphen and no trailing slash.

## First start

1. Create the data dirs: `mkdir -p <data dir>/{minio,redis,upload-tmp,beat,backups/postgres}`.
2. Create the database and role on the shared Postgres server, as its superuser:

   ```sql
   CREATE ROLE circles LOGIN CONNECTION LIMIT 40;
   \password circles
   CREATE DATABASE circles OWNER circles;
   REVOKE CONNECT ON DATABASE circles FROM PUBLIC;
   ```

3. Start Redis and MinIO, then create the bucket:

   ```sh
   docker compose -f docker-compose.prod.yml --env-file <compose env> up -d circles-redis circles-minio
   docker compose -f docker-compose.prod.yml --env-file <compose env> --profile init run --rm circles-minio-init
   ```

4. Create the bucket-scoped app user, as described in [MinIO app user](#minio-app-user).
5. Migrate on purpose, as described in [Migrations](#migrations), then create an admin with
   `... run --rm circles-web python manage.py createsuperuser`.
6. Start everything: `docker compose -f docker-compose.prod.yml --env-file <compose env> up -d`.
7. Check it:
   - `curl -fsS http://127.0.0.1:8110/health/` answers 200. It is plain HTTP and is not redirected.
   - `curl -H "Authorization: Bearer <metrics token>" http://<LAN host>:8110/metrics` answers 200.
     Without the token it answers 401.
   - `docker compose -f docker-compose.prod.yml ps` shows `circles-web` as healthy.

`docker-compose.prod.yml` is a separate project (`name: circles`). Keep it out of any
all-stacks wrapper, so routine "pull everything and restart" runs never touch production.

## Migrations

Containers never migrate on start. `circles-web` sets `RUN_MIGRATIONS=0`, and the entrypoint then
skips `migrate` but still runs `collectstatic`. Without the variable the image keeps its old
behaviour and migrates.

To promote a release:

```sh
git fetch --tags && git checkout <tag>                      # the clone the compose file runs from
export CIRCLES_IMAGE=ghcr.io/ljmerza/circles:<tag>          # or set it in the compose env file
docker compose -f docker-compose.prod.yml --env-file <compose env> pull circles-web
docker compose -f docker-compose.prod.yml --env-file <compose env> run --rm circles-web python manage.py migrate --plan
# Review the plan, then back up before changing the schema:
docker compose -f docker-compose.prod.yml --env-file <compose env> exec circles-pg-backup pg-backup.sh once
docker compose -f docker-compose.prod.yml --env-file <compose env> run --rm circles-web python manage.py migrate
docker compose -f docker-compose.prod.yml --env-file <compose env> up -d
```

Arguments passed to `run` bypass the entrypoint's web start-up (`exec "$@"`), so `run --rm
circles-web python manage.py …` runs just that command.

To roll back, check out the previous tag and set its image. If the release had migrations, either
migrate back first (`manage.py migrate <app> <previous migration>`) or restore the dump taken
before it.

## MinIO app user

The app should not use the root credentials. Create a user that can reach only the bucket:

```sh
cat > /tmp/circles-app-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetBucketLocation", "s3:ListBucket", "s3:ListBucketMultipartUploads"],
      "Resource": ["arn:aws:s3:::circles-media"]
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject",
                 "s3:AbortMultipartUpload", "s3:ListMultipartUploadParts"],
      "Resource": ["arn:aws:s3:::circles-media/*"]
    }
  ]
}
EOF

docker run --rm -it --network circles_backend --env-file <minio env file> \
  -v /tmp/circles-app-policy.json:/policy.json:ro --entrypoint /bin/sh <mc image> -c '
    mc alias set prod http://circles-minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" &&
    mc admin policy create prod circles-app /policy.json &&
    mc admin user add prod <app access key> <app secret key> &&
    mc admin policy attach prod circles-app --user <app access key> &&
    mc anonymous get prod/circles-media'
```

`mc anonymous get` must print `Access permission for ... is private`. The app hands browsers
presigned URLs, so the bucket never needs a public policy. The `<mc image>` is the same image as
`CIRCLES_MC_IMAGE`; see the next section.

## MinIO image availability

`minio/minio` and `minio/mc` stopped serving pulls. On 2026-10-04 both Docker Hub and
`quay.io/minio/*` denied anonymous pulls, including the pinned release tags. The compose file pins
them by digest, so they only resolve on a host that already has them cached. Keep a copy:

```sh
docker save minio/minio@sha256:14cea493d9a34af32f524e538b8346cf79f3321eff8e708c1e2960462bd8936e \
            minio/mc@sha256:a7fe349ef4bd8521fb8497f55c6042871b2ae640607cf99d9bede5e9bdf11727 \
  | gzip > <backup dir>/minio-images.tar.gz
# restore: gunzip -c <backup dir>/minio-images.tar.gz | docker load
```

If you build or mirror MinIO elsewhere, point `CIRCLES_MINIO_IMAGE` / `CIRCLES_MC_IMAGE` at it.

## Upload size

Each file goes up in its own request: `POST /api/keeps/upload/`, carrying the file, an optional
video poster frame (at most 10 MiB) and a few form fields. Several caps apply:

| Layer | Cap | What the user sees |
|---|---|---|
| The SPA composer | `GET /api/keeps/upload/limits/` (from `MAX_UPLOAD_SIZE` / `MAX_VIDEO_UPLOAD_SIZE`) | "<file> is too large. The limit is 90 MB." The file is refused before it is sent. |
| Django | `MAX_UPLOAD_SIZE` (photos), `MAX_VIDEO_UPLOAD_SIZE` (videos) | 413 JSON `file_too_large` |
| The image's nginx | Set at start to the largest allowed file + 10 MiB poster + 1 MiB overhead (`manage.py upload_body_limit`) | 413 JSON `file_too_large` for `/api/` |
| Cloudflare (Free/Pro) | 100 MB per request | A Cloudflare 413 page |

Behind Cloudflare, set both limits to 90 MiB (`94371840`). A file plus a typical poster then stays
under 100 MB, and the composer turns away anything larger with its own message. nginx's cap comes
from the same settings, so it never cuts off a file the app accepts. Without Cloudflare, raise the
limits (the defaults are 100 MiB photos and 1 GiB videos); nginx follows when the container
restarts.

nginx buffers the whole request body before passing it to gunicorn, so a slow upload does not run
into gunicorn's 60-second worker timeout.

## Reverse proxy and client IPs

The image's nginx trusts forwarded headers only from loopback and Docker's `172.16.0.0/12`. That
is where a reverse proxy reaches a published container port from.

- **Client IP:** realip walks `X-Forwarded-For` from the right past those addresses. Django gets
  that one address.
- **Scheme:** `X-Forwarded-Proto` is believed only from those peers, and only as `http`/`https`.
  Anyone else, such as a LAN client on port 8110, gets nginx's own scheme, so they can't claim https.
- **`/metrics`:** proxied only for loopback, Docker and private (RFC 1918) client addresses.
  Everyone else gets 403. Have the public vhost 404 `/metrics` as well. The bearer token is the
  real guard.
- **`/health/` and `/metrics`** are exempt from Django's HTTPS redirect (`SECURE_REDIRECT_EXEMPT`),
  so healthchecks and Prometheus can use plain HTTP. Their `Host` must still be in
  `DJANGO_ALLOWED_HOSTS`.

The upstream proxy must append the real visitor address to `X-Forwarded-For` (behind Cloudflare,
restore it from `CF-Connecting-IP` first) and set `X-Forwarded-Proto https`.

## Backups

`circles-pg-backup` runs `pg_dump -Fc` daily at 03:30 in `CIRCLES_TZ`. It writes
`<data dir>/backups/postgres/circles-YYYYmmdd-HHMMSS.dump` and deletes dumps older than 14 days.
A failed dump is logged, and the next day's run still happens.

```sh
# Dump now:
docker compose -f docker-compose.prod.yml --env-file <compose env> exec circles-pg-backup pg-backup.sh once
# Check the latest dump is readable:
docker compose -f docker-compose.prod.yml --env-file <compose env> exec circles-pg-backup \
  sh -c 'pg_restore --list "$(ls -1t /backups/circles-*.dump | head -1)" | head'
```

Restore, with the app stopped so nothing writes during it:

```sh
docker compose -f docker-compose.prod.yml --env-file <compose env> stop circles-web circles-worker circles-beat
docker compose -f docker-compose.prod.yml --env-file <compose env> exec circles-pg-backup sh -c \
  'PGPASSWORD="$POSTGRES_PASSWORD" pg_restore --clean --if-exists --no-owner --role=circles \
     -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" /backups/<dump file>'
docker compose -f docker-compose.prod.yml --env-file <compose env> start circles-web circles-worker circles-beat
```

To restore into a fresh database instead, create it (owner `circles`) and point `-d` at it.
Test a restore every few months.

Media lives in `<data dir>/minio`. Back up that directory with the host's file backups. To get
plain files instead, `mc mirror` the bucket. The env files and the Fernet key also belong in a
password manager.
