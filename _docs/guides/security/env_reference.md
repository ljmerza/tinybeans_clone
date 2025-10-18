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
| `POSTGRES_*` | `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT` configure the PostgreSQL connection. | `tinybeans`, `tinybeans`, `tinybeans`, `localhost`, `5432` | All |
| `REDIS_URL` | Redis connection string for cache + Celery broker. | `redis://127.0.0.1:6379/0` | All |
| `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Override Celery transport if Redis not used. | `REDIS_URL` | Optional |
| `MAILJET_API_KEY`, `MAILJET_API_SECRET` | Mailjet credentials for transactional email. Leave empty to disable Mailjet. | Empty | Staging, Production |
| `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET_NAME` | MinIO/S3 storage configuration. | `http://minio:9020`, `minioadmin`, `minioadmin`, `tinybeans-media` | All |
| `TWOFA_ENCRYPTION_KEY` | Base64 Fernet key for encrypting TOTP secrets. | Generated in debug mode. | Staging, Production |
| `TWOFA_TRUSTED_DEVICE_SIGNING_KEY` | Optional override for trusted-device cookie signer. Falls back to `DJANGO_SECRET_KEY`. | None | Optional |
| `TWOFA_TRUSTED_DEVICE_ROTATION_DAYS` | Days before a remembered device is reissued with a new signed token. | `15` | Optional |
| `MAGIC_LOGIN_TOKEN_SIGNING_KEY` | Optional override for passwordless token HMAC. Falls back to `DJANGO_SECRET_KEY`. | None | Optional |
| `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET` | Google OAuth credentials. | Empty | Staging, Production |
| `ACCOUNT_FRONTEND_BASE_URL` | Base URL for account-related email links. | `http://localhost:3000` | All |

For additional feature-specific toggles see inline documentation in `mysite/mysite/config/settings/base.py`.
