# Backend Environment Reference

The table below summarizes the required runtime environment variables for the Django stack.

| Variable | Description | Default | Required In |
| --- | --- | --- | --- |
| `DJANGO_SECRET_KEY` | Cryptographic signing key for Django. Set to a strong random value in staging/production. | Auto-generated when `DJANGO_DEBUG=1`. | Staging, Production |
| `DJANGO_DEBUG` | Enables Django debug mode when truthy. Managed automatically by `mysite.config.settings.<env>`. | `1` in `local`, `0` otherwise. | All |
| `DJANGO_ENVIRONMENT` | Human-readable environment label used by startup helpers to pick the correct settings module. | `local` | All |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hostnames served by Django. Wildcards are rejected when `DEBUG=0`. | `localhost,127.0.0.1,[::1],web` | Staging, Production |
| `DJANGO_SECURE_SSL_REDIRECT` | Forces HTTPS redirects. Defaults to `True` outside local. | `False` when `DEBUG=1`. | Staging, Production |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Comma-separated CSRF origins. Must be set for non-local deployments. | Local dev origins when `DEBUG=1`. | Staging, Production |
| `POSTGRES_*` | `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT` configure the PostgreSQL connection. | `circles`, `circles`, `circles`, `localhost`, `5432` | All |
| `REDIS_URL` | Redis connection string for cache + Celery broker. | `redis://127.0.0.1:6379/0` | All |
| `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Override Celery transport if Redis not used. | `REDIS_URL` | Optional |
| `MAILJET_API_KEY`, `MAILJET_API_SECRET` | Mailjet credentials for transactional email. Leave empty to disable Mailjet. | Empty | Staging, Production |
| `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET_NAME` | MinIO/S3 storage configuration. | `http://minio:9020`, `minioadmin`, `minioadmin`, `circles-media` | All |
| `TWOFA_ENCRYPTION_KEY` | Base64 Fernet key for encrypting TOTP secrets. | Generated in debug mode. | Staging, Production |
| `TWOFA_TRUSTED_DEVICE_SIGNING_KEY` | Optional override for trusted-device cookie signer. Falls back to `DJANGO_SECRET_KEY`. | None | Optional |
| `TWOFA_TRUSTED_DEVICE_ROTATION_DAYS` | Days before a remembered device is reissued with a new signed token. | `15` | Optional |
| `MAGIC_LOGIN_TOKEN_SIGNING_KEY` | Optional override for passwordless token HMAC. Falls back to `DJANGO_SECRET_KEY`. | None | Optional |
| `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET` | Google OAuth credentials. | Empty | Staging, Production |
| `OAUTH_ALLOWED_REDIRECT_URIS` | Comma-separated exact redirect URIs Google sign-in accepts. The SPA sends `<origin>/auth/google-callback`, so list one per origin, e.g. `https://app.example.com/auth/google-callback`. Each must also be an authorized redirect URI on the Google OAuth client. | `http://localhost:3053/…`, `http://127.0.0.1:3053/…`, `http://localhost:3000/…` when `DEBUG=1`; empty otherwise | Staging, Production (if Google sign-in is used) |
| `MAX_UPLOAD_SIZE`, `MAX_VIDEO_UPLOAD_SIZE` | Largest accepted photo / video in bytes. The SPA reads them from `GET /api/keeps/upload/limits/`, and the production image's nginx derives its `client_max_body_size` from them at start. Behind Cloudflare's 100 MB request cap use `94371840` (90 MiB) for both. | `104857600` (100 MiB), `1073741824` (1 GiB) | Optional |
| `RUN_MIGRATIONS` | Production image only. `0` makes the entrypoint skip `migrate` on start (it still runs `collectstatic`); `docker-compose.prod.yml` sets it. See [deployment/production.md](../deployment/production.md). | `1` (migrate on start) | Production |
| `FLOWER_BASIC_AUTH` | `<user>:<password>` for the Flower dashboard, which has no login otherwise. Read by Flower itself. | Empty (no auth) | Production (if Flower runs) |
| `DJANGO_TRUST_FORWARDED_FOR` | Read `X-Forwarded-For` / `X-Real-IP` when resolving the client IP for rate limits, throttles and audit data. Outside DEBUG it only counts when the immediate peer is in `DJANGO_TRUSTED_PROXY_IPS`. | `1` when `DEBUG=1`, else `0` | Production behind a proxy |
| `DJANGO_TRUSTED_PROXY_IPS` | Comma-separated proxy addresses or CIDR ranges. `X-Forwarded-For` is walked from the right past these; the first other address is the client. The production image's nginx talks to gunicorn on loopback, so use `127.0.0.1,::1` there. An invalid entry fails at startup. | `127.0.0.1,::1` when `DEBUG=1`, else empty | Production behind a proxy |
| `RATELIMIT_ENABLE` | django-ratelimit on/off. The dev compose file sets `0`; do not carry that into production. | `0` when `DEBUG=1`, else `1` | Optional |
| `ACCOUNT_FRONTEND_BASE_URL` | Base URL for account-related email links. | `http://localhost:3000` | All |
| `METRICS_TOKEN` | Bearer token Prometheus must send to `GET /metrics`. Empty turns the endpoint off (404). See [monitoring.md](../monitoring.md). | Empty (off) | Optional |

For additional feature-specific toggles see inline documentation in `mysite/mysite/config/settings/base.py`.
