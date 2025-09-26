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

All tests target the local PostgreSQL instance specified in `docker-compose.yml`. After starting the services, run:

```bash
python manage.py test
```

Set `CELERY_TASK_ALWAYS_EAGER=1` in the environment when you need Celery tasks (including email dispatch) to execute synchronously during debugging or testing.

## Useful Commands

- Lint formatting: `ruff check .`
- Format code: `ruff format .`
- Open Django shell with project context: `python manage.py shell_plus`

Feel free to extend the demo data to cover new features—just update the seeding command and this document accordingly.
