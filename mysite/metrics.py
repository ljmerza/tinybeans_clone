"""Prometheus metrics for the backend: dependency health and Postgres connection use.

``GET /metrics`` returns the Prometheus text format (version 0.0.4). Only the host's
Prometheus should read it, so it needs ``Authorization: Bearer <METRICS_TOKEN>``. While
METRICS_TOKEN is empty the endpoint answers 404. nginx does not proxy /metrics to
Django, so Prometheus scrapes the web container's published port directly.

Each dependency is checked in its own thread with a short client timeout. A hung
dependency is then reported as ``circles_dependency_up 0`` and the scrape still returns.
The checks open their own short-lived clients instead of using Django's connections.
A scrape therefore never keeps a database connection open (the 2026-10-02 leak), and it
still works when Django's own connection is broken.
"""

from __future__ import annotations

import hmac
import logging
import math
import platform
import re
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, wait
from urllib.parse import urlparse

import django
import psycopg
import redis
import urllib3
from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed, HttpResponseNotFound
from django.views.decorators.cache import never_cache
from minio import Minio

logger = logging.getLogger(__name__)

CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"

# Timeout in seconds for each client operation (connect, query, ping, HTTP read).
# Healthy checks take milliseconds on the compose network.
CHECK_TIMEOUT = 2
# How long the view waits for all checks. A check still running after this is
# reported as down. Postgres can use a connect timeout plus a statement timeout,
# so this is a bit more than twice CHECK_TIMEOUT.
CHECKS_DEADLINE = 5.0

# Keys Django accepts in DATABASES OPTIONS that libpq does not.
_DJANGO_ONLY_DB_OPTIONS = {"isolation_level", "assume_role", "server_side_binding", "pool"}

# Client backends are the connections that count against max_connections.
CONNECTIONS_SQL = """
SELECT coalesce(state, 'unknown'), count(*)
FROM pg_stat_activity
WHERE backend_type = 'client backend'
GROUP BY 1
"""
# Exported even at zero so the series don't disappear between scrapes.
_PG_STATES = ("active", "idle", "idle in transaction", "idle in transaction (aborted)")

# (metric name, labels, value)
Sample = tuple[str, dict[str, str], float]

# Every exported metric, in output order, with its HELP text. All are gauges.
METRICS = {
    "circles_dependency_up": "1 if the dependency answered within the timeout, else 0.",
    "circles_dependency_check_duration_seconds": "Seconds the dependency check took.",
    "circles_postgres_connections": (
        "Client connections on the Postgres server by state, across all databases. "
        "Includes the scrape's own connection."
    ),
    "circles_postgres_max_connections": "The Postgres max_connections setting.",
    "circles_celery_queue_length": "Messages waiting in a Celery queue on the Redis broker.",
    "circles_app_info": "Backend runtime versions. Always 1.",
    "circles_metrics_scrape_duration_seconds": "Seconds taken to build this metrics response.",
}


# --- Dependency checks -------------------------------------------------------
# Each check raises on failure. On success it returns any extra samples it gathered.


def database_params(db: dict) -> dict | None:
    """libpq parameters for a short-lived connection to a DATABASES entry, or None if it isn't Postgres."""
    if "postgresql" not in db["ENGINE"]:
        return None
    params = {key: value for key, value in db.get("OPTIONS", {}).items() if key not in _DJANGO_ONLY_DB_OPTIONS}
    for key, setting in (("dbname", "NAME"), ("user", "USER"), ("password", "PASSWORD"), ("host", "HOST")):
        if db.get(setting):
            params[key] = db[setting]
    if db.get("PORT"):
        params["port"] = int(db["PORT"])
    statement_timeout = f"-c statement_timeout={CHECK_TIMEOUT * 1000}"
    params["options"] = f"{params['options']} {statement_timeout}" if params.get("options") else statement_timeout
    params["connect_timeout"] = max(CHECK_TIMEOUT, 2)  # libpq treats anything lower as 2
    params["application_name"] = "circles-metrics"
    return params


def check_database(params: dict) -> list[Sample]:
    with psycopg.connect(autocommit=True, **params) as conn, conn.cursor() as cur:
        cur.execute(CONNECTIONS_SQL)
        rows = cur.fetchall()
        cur.execute("SELECT current_setting('max_connections')::int")
        (max_connections,) = cur.fetchone()

    by_state = dict.fromkeys(_PG_STATES, 0)
    for state, count in rows:
        by_state[state] = by_state.get(state, 0) + count
    samples: list[Sample] = [
        ("circles_postgres_connections", {"state": _snake_case(state)}, count) for state, count in by_state.items()
    ]
    samples.append(("circles_postgres_max_connections", {}, max_connections))
    return samples


def _redis_client(url: str) -> redis.Redis:
    return redis.Redis.from_url(
        url, socket_connect_timeout=CHECK_TIMEOUT, socket_timeout=CHECK_TIMEOUT, retry_on_timeout=False
    )


def check_redis(url: str) -> list[Sample]:
    client = _redis_client(url)
    try:
        client.ping()
    finally:
        client.close()
    return []


def check_celery_broker(url: str, queues: list[str]) -> list[Sample]:
    """Ping the broker and read each queue's length (kombu keeps a Redis list per queue)."""
    client = _redis_client(url)
    try:
        client.ping()
        pipe = client.pipeline(transaction=False)
        for queue in queues:
            pipe.llen(queue)
        lengths = pipe.execute()
    finally:
        client.close()
    return [
        ("circles_celery_queue_length", {"queue": queue}, length) for queue, length in zip(queues, lengths, strict=True)
    ]


def check_object_storage() -> list[Sample]:
    """HEAD the media bucket, which also checks the credentials."""
    parsed = urlparse(settings.MINIO_ENDPOINT)
    http = urllib3.PoolManager(
        timeout=urllib3.Timeout(connect=CHECK_TIMEOUT, read=CHECK_TIMEOUT),
        retries=urllib3.Retry(total=0),
    )
    try:
        client = Minio(
            parsed.netloc or settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_USE_SSL,
            # A known region skips the bucket-location lookup request.
            region=settings.MINIO_REGION,
            http_client=http,
        )
        if not client.bucket_exists(settings.MINIO_BUCKET_NAME):
            raise RuntimeError(f"bucket {settings.MINIO_BUCKET_NAME!r} does not exist")
    finally:
        http.clear()
    return []


def _is_redis_url(url: str) -> bool:
    return urlparse(url or "").scheme in {"redis", "rediss", "unix"}


def build_checks() -> dict[str, Callable[[], list[Sample]]]:
    """Checks for the dependencies this deployment is configured with."""
    checks: dict[str, Callable[[], list[Sample]]] = {}
    db_params = database_params(settings.DATABASES["default"])
    if db_params is not None:
        checks["database"] = lambda: check_database(db_params)
    redis_url = getattr(settings, "REDIS_URL", "")
    if _is_redis_url(redis_url):
        checks["redis"] = lambda: check_redis(redis_url)
    broker_url = getattr(settings, "CELERY_BROKER_URL", "")
    if _is_redis_url(broker_url):
        queues = [queue.name for queue in getattr(settings, "CELERY_TASK_QUEUES", ())]
        checks["celery_broker"] = lambda: check_celery_broker(broker_url, queues)
    if getattr(settings, "MINIO_ENDPOINT", ""):
        checks["object_storage"] = check_object_storage
    return checks


def _timed(name: str, check: Callable[[], list[Sample]]) -> tuple[bool, float, list[Sample]]:
    start = time.monotonic()
    try:
        samples = check()
    except Exception as exc:
        logger.warning("metrics: %s check failed: %s", name, exc)
        return False, time.monotonic() - start, []
    return True, time.monotonic() - start, samples


def run_checks(checks: dict[str, Callable[[], list[Sample]]]) -> list[Sample]:
    """Run the checks in parallel and return their samples, plus up and duration per dependency."""
    if not checks:
        return []
    pool = ThreadPoolExecutor(max_workers=len(checks), thread_name_prefix="metrics-check")
    futures = {name: pool.submit(_timed, name, check) for name, check in checks.items()}
    wait(futures.values(), timeout=CHECKS_DEADLINE)
    # Don't wait for a hung check; its own client timeout ends the thread soon after.
    pool.shutdown(wait=False, cancel_futures=True)

    samples: list[Sample] = []
    for name, future in futures.items():
        if future.done():
            up, duration, extra = future.result()
        else:
            logger.warning("metrics: %s check did not finish within %ss", name, CHECKS_DEADLINE)
            up, duration, extra = False, CHECKS_DEADLINE, []
        samples.append(("circles_dependency_up", {"dependency": name}, int(up)))
        samples.append(("circles_dependency_check_duration_seconds", {"dependency": name}, duration))
        samples.extend(extra)
    return samples


def collect() -> list[Sample]:
    start = time.monotonic()
    samples = run_checks(build_checks())
    samples.append(
        (
            "circles_app_info",
            {"django_version": django.get_version(), "python_version": platform.python_version()},
            1,
        )
    )
    samples.append(("circles_metrics_scrape_duration_seconds", {}, time.monotonic() - start))
    return samples


# --- Text exposition format ----------------------------------------------------


def _snake_case(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "unknown"


def _escape_label(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _format_value(value: float) -> str:
    if isinstance(value, bool):
        return str(int(value))
    if isinstance(value, int):
        return str(value)
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "+Inf" if value > 0 else "-Inf"
    return repr(float(value))


def render(samples: list[Sample]) -> str:
    """Render samples as Prometheus text format, grouped per metric with HELP and TYPE lines."""
    by_name: dict[str, list[Sample]] = {}
    for sample in samples:
        if sample[0] not in METRICS:
            raise ValueError(f"unknown metric {sample[0]!r}")
        by_name.setdefault(sample[0], []).append(sample)

    lines: list[str] = []
    for name, help_text in METRICS.items():
        if name not in by_name:
            continue
        lines.append(f"# HELP {name} {help_text}")
        lines.append(f"# TYPE {name} gauge")
        for _, labels, value in by_name[name]:
            label_text = ",".join(f'{key}="{_escape_label(val)}"' for key, val in labels.items())
            series = f"{name}{{{label_text}}}" if label_text else name
            lines.append(f"{series} {_format_value(value)}")
    return "\n".join(lines) + "\n"


# --- View ------------------------------------------------------------------------


def _has_valid_token(request: HttpRequest, token: str) -> bool:
    scheme, _, credentials = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() != "bearer":
        return False
    return hmac.compare_digest(credentials.strip().encode(), token.encode())


@never_cache
def metrics_view(request: HttpRequest) -> HttpResponse:
    token = settings.METRICS_TOKEN
    if not token:
        return HttpResponseNotFound()
    if not _has_valid_token(request, token):
        response = HttpResponse("Unauthorized\n", status=401, content_type="text/plain; charset=utf-8")
        response["WWW-Authenticate"] = 'Bearer realm="metrics"'
        return response
    if request.method not in ("GET", "HEAD"):
        return HttpResponseNotAllowed(["GET", "HEAD"])
    return HttpResponse(render(collect()), content_type=CONTENT_TYPE)
