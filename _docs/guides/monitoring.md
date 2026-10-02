# Backend metrics (Prometheus)

`GET /metrics` on the Django backend returns Prometheus text format (0.0.4). It reports
whether each dependency answers and how many Postgres connections are in use. It was added
after the 2026-10-02 outage: the runserver `web` service leaked idle Postgres connections
until all 100 `max_connections` slots were taken, and every login returned 500
("sorry, too many clients already").

Code: `mysite/metrics.py`. Tests: `mysite/tests/test_metrics.py`.

## Access

- **Off by default.** With `METRICS_TOKEN` empty the endpoint answers 404.
- **Bearer token.** Requests need `Authorization: Bearer <METRICS_TOKEN>`. A missing or wrong
  token gets 401. The token is compared in constant time.
- **Not behind nginx.** The circles nginx vhost only proxies `/api/`, `/admin/`, `/static/`,
  `/media/` and `/health/` to Django. Everything else, including `/metrics`, goes to the SPA.
  Prometheus scrapes the web container's published port (`192.168.1.76:8100`) directly.
  Don't add a `/metrics` location to nginx.

## Metrics

All are gauges.

| Metric | Labels | Meaning |
| --- | --- | --- |
| `circles_dependency_up` | `dependency` = `database`, `redis`, `celery_broker`, `object_storage` | 1 if the dependency answered within the timeout, else 0 |
| `circles_dependency_check_duration_seconds` | `dependency` | How long that check took |
| `circles_postgres_connections` | `state` = `active`, `idle`, `idle_in_transaction`, `idle_in_transaction_aborted` (others if Postgres reports them) | Client connections on the whole Postgres server, from `pg_stat_activity`. Includes the scrape's own connection (one `active`). |
| `circles_postgres_max_connections` | | Postgres `max_connections` |
| `circles_celery_queue_length` | `queue` = `email`, `sms`, `media`, `maintenance` | Messages waiting in each Celery queue on the Redis broker |
| `circles_app_info` | `django_version`, `python_version` | Always 1 |
| `circles_metrics_scrape_duration_seconds` | | Time taken to build the response |

The `circles_postgres_*` and `circles_celery_queue_length` series are missing while their
dependency is down.

How the checks work:

- The checks run in parallel threads. Each client has a 2 s timeout (Postgres
  `connect_timeout` plus `statement_timeout`, Redis socket timeouts, MinIO
  connect/read timeouts with no retries). The view stops waiting after 5 s and reports
  any unfinished check as down. A hung dependency therefore can't hang the scrape.
- Every check opens its own short-lived client and closes it afterwards. The Postgres
  check uses a separate connection named `circles-metrics`, not Django's connection, so a
  scrape never holds a connection open.
- A healthy scrape takes about 25 ms. It costs one Postgres connection, two Redis
  round-trips and one MinIO `HEAD` on the bucket.
- `database` is only checked when the default database is Postgres, not with the SQLite
  fallback. `celery_broker` is only checked when the broker URL is Redis.

## Enabling it

1. Generate a token with `openssl rand -hex 32`. Set `METRICS_TOKEN=<token>` in
   `tinybeans_copy/.env`. Compose substitutes it into the `web` service's `environment:`.
   Putting it in `.env.development` has no effect, because the `environment:` entry
   overrides `env_file:`.
2. Recreate the web container so it picks up the new variable:
   `docker compose up -d web`. Runserver's autoreload does not reload environment variables.
3. Write the same token to `/media/cubxi/docker/volumes/prometheus/config/circles_metrics_token`.
   The Prometheus container sees that file as `/etc/prometheus/circles_metrics_token`.
   It must be readable by the container user.
4. Add the scrape job and alert rules below, then reload Prometheus with
   `docker kill -s HUP prometheus`.
5. Check the endpoint:
   `curl -s -H "Authorization: Bearer $(cat /media/cubxi/docker/volumes/prometheus/config/circles_metrics_token)" http://192.168.1.76:8100/metrics`

## Suggested Prometheus config

Scrape job for `prometheus.yml`, under `scrape_configs:`:

```yaml
  - job_name: circles_web
    # circles.lmerza.com Django backend (projects/tinybeans_copy, its own compose project).
    # /metrics needs the bearer token that is set as METRICS_TOKEN in tinybeans_copy/.env.
    scrape_interval: 30s
    authorization:
      type: Bearer
      credentials_file: /etc/prometheus/circles_metrics_token
    static_configs:
      - targets: ['192.168.1.76:8100']
```

Alert group for `alert.rules.yml`, under `groups:`:

```yaml
  - name: Circles Web Alerts
    rules:
      - alert: Circles Postgres Connections High
        # The 2026-10-02 outage: leaked idle connections filled all 100 slots and every login 500'd.
        expr: sum(circles_postgres_connections) / max(circles_postgres_max_connections) > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "circles Postgres is at {{ $value | humanizePercentage }} of max_connections"
          description: "Over 80% of Postgres connection slots have been in use for 5 minutes. Check circles_postgres_connections by state; a growing idle count means a connection leak. Run `SELECT application_name, client_addr, state, count(*) FROM pg_stat_activity GROUP BY 1,2,3` in the tinybeans_copy postgres container."

      - alert: Circles Dependency Down
        expr: circles_dependency_up == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "circles backend cannot reach {{ $labels.dependency }}"
          description: "The circles web container's {{ $labels.dependency }} check has failed for 2 minutes. If dependency=database, Postgres may be refusing clients because max_connections is used up. Check `docker compose ps` and logs in projects/tinybeans_copy."

      - alert: Circles Metrics Down
        # The web container or runserver is down, or the scrape token is wrong (401).
        expr: up{job="circles_web"} == 0 or absent(up{job="circles_web"})
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "circles backend metrics are unreachable"
          description: "Prometheus cannot scrape http://192.168.1.76:8100/metrics. Check the Prometheus targets page for the error. A 404 means METRICS_TOKEN is not set; a 401 means the token doesn't match circles_metrics_token."
```

Optional fourth rule, if Celery backlogs turn out to matter:

```yaml
      - alert: Circles Celery Queue Backlog
        expr: circles_celery_queue_length > 50
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "circles Celery queue {{ $labels.queue }} has {{ $value }} waiting tasks"
          description: "Tasks are piling up; the celery-worker-1 container may be down or stuck."
```
