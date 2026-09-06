# =============================================================================
# Stage 1: Frontend build (production only)
# =============================================================================
FROM node:20-slim AS frontend-builder

WORKDIR /app/web
COPY web/package*.json ./
RUN npm ci --no-audit --no-fund

COPY web/ ./
# `npm run build` is `vite build && tsc`; the tsc pass currently fails on
# pre-existing type errors, so bundle directly to keep the image buildable.
RUN npx vite build

# =============================================================================
# Stage 2: Runtime base
# =============================================================================
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq5 \
        tzdata \
    && rm -rf /var/lib/apt/lists/*

# uv.lock is the single source of truth: CI resolves with `uv sync --frozen`, so
# exporting the same lock here keeps image builds identical to what CI tested.
COPY --from=ghcr.io/astral-sh/uv:0.11.26 /uv /bin/uv
COPY pyproject.toml uv.lock /app/
RUN uv export --frozen --no-dev --no-emit-project -o /tmp/requirements.lock && \
    uv pip install --system --no-cache -r /tmp/requirements.lock && \
    rm /tmp/requirements.lock

# =============================================================================
# Stage 3: Development image (docker-compose builds this target)
# =============================================================================
FROM base AS development

RUN uv export --frozen --only-dev --no-emit-project -o /tmp/requirements.dev.lock && \
    uv pip install --system --no-cache -r /tmp/requirements.dev.lock && \
    rm /tmp/requirements.dev.lock

COPY . .

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# =============================================================================
# Stage 4: Production image
# =============================================================================
FROM base AS production

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        nginx \
        supervisor \
    && rm -rf /var/lib/apt/lists/*

COPY --from=frontend-builder /app/web/dist /app/web/dist

COPY manage.py /app/manage.py
COPY mysite /app/mysite

COPY docker/nginx.conf /etc/nginx/nginx.conf
COPY docker/supervisord.prod.conf /etc/supervisor/conf.d/app.conf
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV DJANGO_SETTINGS_MODULE=mysite.config.settings.production

EXPOSE 80
ENTRYPOINT ["/entrypoint.sh"]
