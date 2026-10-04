"""Tests for the Prometheus /metrics endpoint."""

from __future__ import annotations

import re
import time
from unittest import mock

import psycopg
import pytest
import redis
from django.test import override_settings

from mysite import metrics

TOKEN = "s3cret-metrics-token"
AUTH = {"HTTP_AUTHORIZATION": f"Bearer {TOKEN}"}

# name{labels} value -- the sample line shape of the text exposition format
SAMPLE_LINE = re.compile(r'^[a-zA-Z_:][a-zA-Z0-9_:]*(\{([a-zA-Z_][a-zA-Z0-9_]*="([^"\\]|\\.)*",?)*\})? \S+$')

POSTGRES_DB = {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": "circles",
    "USER": "circles",
    "PASSWORD": "pw",
    "HOST": "postgres",
    "PORT": "5432",
    "OPTIONS": {"sslmode": "prefer", "isolation_level": 1},
}


class FakeCursor:
    def __init__(self, rows, max_connections=100):
        self.rows = rows
        self.max_connections = max_connections
        self.executed: list[str] = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql):
        self.executed.append(sql)

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return (self.max_connections,)


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def cursor(self):
        return self._cursor


def parse(body: str) -> dict[str, float]:
    """Map each `name{labels}` series to its value, checking every line's syntax."""
    assert body.endswith("\n")
    series = {}
    for line in body.splitlines():
        if line.startswith("#"):
            assert re.match(r"^# (HELP|TYPE) [a-z_]+ .+$", line), line
            continue
        assert SAMPLE_LINE.match(line), line
        key, value = line.rsplit(" ", 1)
        series[key] = float(value)
    return series


@pytest.fixture
def healthy(monkeypatch):
    """Every dependency answers; Postgres reports 3 active and 40 idle connections."""
    cursor = FakeCursor([("active", 3), ("idle", 40)])
    monkeypatch.setattr(metrics.psycopg, "connect", mock.Mock(return_value=FakeConnection(cursor)))

    redis_client = mock.Mock()
    redis_client.pipeline.return_value.execute.return_value = [0, 0, 7, 0]
    monkeypatch.setattr(metrics.redis.Redis, "from_url", mock.Mock(return_value=redis_client))

    minio_client = mock.Mock()
    minio_client.bucket_exists.return_value = True
    monkeypatch.setattr(metrics, "Minio", mock.Mock(return_value=minio_client))
    return {"cursor": cursor, "redis": redis_client, "minio": minio_client}


@pytest.fixture
def postgres_settings(monkeypatch):
    # The test settings use SQLite; point only the metrics check at a (fake) Postgres.
    real_database_params = metrics.database_params
    monkeypatch.setattr(metrics, "database_params", lambda db: real_database_params(POSTGRES_DB))
    with override_settings(
        REDIS_URL="redis://redis:6379/0",
        CELERY_BROKER_URL="redis://redis:6379/0",
        MINIO_ENDPOINT="http://minio:9000",
    ):
        yield


# --- auth -------------------------------------------------------------------------


@override_settings(METRICS_TOKEN="")
def test_disabled_when_token_unset(client, healthy):
    assert client.get("/metrics").status_code == 404
    assert client.get("/metrics", **AUTH).status_code == 404


@override_settings(METRICS_TOKEN=TOKEN)
@pytest.mark.parametrize(
    "header",
    [None, "Bearer wrong-token", f"Basic {TOKEN}", f"Bearer {TOKEN}x", "Bearer ", TOKEN],
)
def test_rejects_missing_or_wrong_token(client, healthy, header):
    extra = {"HTTP_AUTHORIZATION": header} if header is not None else {}
    response = client.get("/metrics", **extra)
    assert response.status_code == 401
    assert response["WWW-Authenticate"].startswith("Bearer")
    assert "circles_" not in response.content.decode()


@override_settings(METRICS_TOKEN=TOKEN)
def test_serves_metrics_with_right_token(client, healthy):
    response = client.get("/metrics", **AUTH)
    assert response.status_code == 200
    assert response["Content-Type"] == "text/plain; version=0.0.4; charset=utf-8"
    assert "no-cache" in response["Cache-Control"]
    series = parse(response.content.decode())
    assert "circles_metrics_scrape_duration_seconds" in series
    assert any(key.startswith("circles_app_info{") for key in series)


@override_settings(METRICS_TOKEN=TOKEN)
def test_bearer_scheme_is_case_insensitive(client, healthy):
    response = client.get("/metrics", HTTP_AUTHORIZATION=f"bearer {TOKEN}")
    assert response.status_code == 200


@override_settings(METRICS_TOKEN=TOKEN)
def test_rejects_non_get_methods(client, healthy):
    assert client.post("/metrics", **AUTH).status_code == 405


# --- collected metrics ------------------------------------------------------------


@pytest.mark.usefixtures("postgres_settings")
def test_all_dependencies_up(healthy):
    series = parse(metrics.render(metrics.collect()))

    for dependency in ("database", "redis", "celery_broker", "object_storage"):
        assert series[f'circles_dependency_up{{dependency="{dependency}"}}'] == 1
        assert series[f'circles_dependency_check_duration_seconds{{dependency="{dependency}"}}'] >= 0

    assert series['circles_postgres_connections{state="active"}'] == 3
    assert series['circles_postgres_connections{state="idle"}'] == 40
    assert series["circles_postgres_max_connections"] == 100
    assert series['circles_celery_queue_length{queue="media"}'] == 7
    assert series['circles_celery_queue_length{queue="email"}'] == 0


def test_connection_query_counts_client_backends_by_state(healthy):
    healthy["cursor"].rows = [("active", 2), ("idle", 95), ("idle in transaction (aborted)", 1), ("unknown", 1)]
    healthy["cursor"].max_connections = 120

    samples = metrics.check_database({"host": "postgres"})

    assert "backend_type = 'client backend'" in healthy["cursor"].executed[0]
    assert "GROUP BY" in healthy["cursor"].executed[0]
    connections = {labels["state"]: value for name, labels, value in samples if name == "circles_postgres_connections"}
    assert connections == {
        "active": 2,
        "idle": 95,
        "idle_in_transaction": 0,  # known states are exported even at zero
        "idle_in_transaction_aborted": 1,
        "unknown": 1,
    }
    assert ("circles_postgres_max_connections", {}, 120) in samples


def test_database_params_bound_the_connection():
    params = metrics.database_params(POSTGRES_DB)

    assert params["host"] == "postgres"
    assert params["port"] == 5432
    assert params["sslmode"] == "prefer"
    assert "isolation_level" not in params  # Django-only option, libpq would reject it
    assert params["connect_timeout"] >= 2
    assert "statement_timeout=" in params["options"]
    assert params["application_name"] == "circles-metrics"


def test_no_database_check_off_postgres():
    # The test settings use SQLite.
    assert metrics.database_params({"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}) is None
    assert "database" not in metrics.build_checks()


@override_settings(CELERY_BROKER_URL="memory://")
def test_no_broker_check_for_non_redis_broker():
    assert "celery_broker" not in metrics.build_checks()


@pytest.mark.usefixtures("postgres_settings")
def test_database_down(healthy, monkeypatch):
    monkeypatch.setattr(
        metrics.psycopg,
        "connect",
        mock.Mock(side_effect=psycopg.OperationalError("sorry, too many clients already")),
    )

    series = parse(metrics.render(metrics.collect()))

    assert series['circles_dependency_up{dependency="database"}'] == 0
    assert series['circles_dependency_up{dependency="redis"}'] == 1
    assert not any(key.startswith("circles_postgres_") for key in series)


@pytest.mark.usefixtures("postgres_settings")
def test_redis_down(healthy):
    healthy["redis"].ping.side_effect = redis.ConnectionError("Connection refused")

    series = parse(metrics.render(metrics.collect()))

    assert series['circles_dependency_up{dependency="redis"}'] == 0
    assert series['circles_dependency_up{dependency="celery_broker"}'] == 0
    assert series['circles_dependency_up{dependency="database"}'] == 1
    assert not any(key.startswith("circles_celery_queue_length") for key in series)
    assert healthy["redis"].close.called


@pytest.mark.usefixtures("postgres_settings")
@pytest.mark.parametrize("failure", ["missing_bucket", "error"])
def test_object_storage_down(healthy, failure):
    if failure == "missing_bucket":
        healthy["minio"].bucket_exists.return_value = False
    else:
        healthy["minio"].bucket_exists.side_effect = OSError("timed out")

    series = parse(metrics.render(metrics.collect()))

    assert series['circles_dependency_up{dependency="object_storage"}'] == 0
    assert series['circles_dependency_up{dependency="database"}'] == 1


def test_hung_check_is_reported_down_without_hanging_the_scrape(monkeypatch):
    monkeypatch.setattr(metrics, "CHECKS_DEADLINE", 0.2)
    checks = {"redis": lambda: time.sleep(2) or [], "database": lambda: []}

    start = time.monotonic()
    samples = metrics.run_checks(checks)
    elapsed = time.monotonic() - start

    assert elapsed < 1
    up = {labels["dependency"]: value for name, labels, value in samples if name == "circles_dependency_up"}
    assert up == {"redis": 0, "database": 1}


def test_client_timeouts_are_set(healthy, monkeypatch):
    metrics.check_redis("redis://redis:6379/0")
    kwargs = metrics.redis.Redis.from_url.call_args.kwargs
    assert kwargs["socket_connect_timeout"] == metrics.CHECK_TIMEOUT
    assert kwargs["socket_timeout"] == metrics.CHECK_TIMEOUT

    with override_settings(MINIO_ENDPOINT="http://minio:9000"):
        metrics.check_object_storage()
    minio_kwargs = metrics.Minio.call_args.kwargs
    assert metrics.Minio.call_args.args[0] == "minio:9000"
    assert minio_kwargs["http_client"].connection_pool_kw["timeout"].connect_timeout == metrics.CHECK_TIMEOUT
    assert minio_kwargs["http_client"].connection_pool_kw["retries"].total == 0


# --- exposition format --------------------------------------------------------------


def test_render_format():
    body = metrics.render(
        [
            ("circles_dependency_up", {"dependency": "database"}, 1),
            ("circles_dependency_up", {"dependency": "redis"}, 0),
            ("circles_postgres_max_connections", {}, 100),
            ("circles_metrics_scrape_duration_seconds", {}, 0.25),
            ("circles_app_info", {"django_version": 'we"ird\\v\n'}, 1),
        ]
    )

    lines = body.splitlines()
    # One HELP and TYPE pair per metric, before its samples, in METRICS order.
    assert lines[:4] == [
        f"# HELP circles_dependency_up {metrics.METRICS['circles_dependency_up']}",
        "# TYPE circles_dependency_up gauge",
        'circles_dependency_up{dependency="database"} 1',
        'circles_dependency_up{dependency="redis"} 0',
    ]
    assert body.count("# TYPE circles_dependency_up gauge") == 1
    assert "circles_postgres_max_connections 100" in lines
    assert "circles_metrics_scrape_duration_seconds 0.25" in lines
    assert 'circles_app_info{django_version="we\\"ird\\\\v\\n"} 1' in lines
    parse(body)


def test_render_rejects_unknown_metric():
    with pytest.raises(ValueError):
        metrics.render([("bogus_metric", {}, 1)])


def test_format_special_values():
    assert metrics._format_value(float("nan")) == "NaN"
    assert metrics._format_value(float("inf")) == "+Inf"
    assert metrics._format_value(True) == "1"
