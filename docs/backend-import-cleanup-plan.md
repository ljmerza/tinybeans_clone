# Backend Import Cleanup Plan

## Objectives
- Remove ad-hoc `sys.path` manipulation and PYTHONPATH overrides so backend code imports cleanly in every runtime (Django, Celery, tests, shells, Docker).
- Flatten the project/package layout into a conventional Django structure that works with default tooling and makes module ownership obvious.
- Update Docker and local tooling so services run against the new layout without bespoke wrappers.

## Current Status
- Standard Django package layout now lives under `mysite/` with Celery, settings, and utilities alongside first-party apps.
- All ad-hoc `sys.path`/`PYTHONPATH` manipulations (`sitecustomize.py`, inline inserts, pytest overrides, docker-compose tweaks) have been removed.
- Imports consolidated under the `mysite.*` namespace, and Django apps are registered via fully qualified dotted paths.
- Docker services continue to run from `/app/mysite` without special environment tweaks; Celery beat/worker entrypoints resolve modules via standard imports.
- Test harness boots with `python -m pytest` or `python manage.py test --settings=mysite.test_settings`; full suite still needs product-side data fixes (see failing assertions in auth/users/email tests).

## Former Pain Points (now addressed)
- Global path injection via `sitecustomize.py:1` kept both the repo root and `mysite/` on `sys.path`, masking structural issues.
- Outer package namespace hacking in `mysite/__init__.py:1` combined two directory trees into a single package.
- Runtime bootstraps (e.g. `manage.py:7`, `mysite/__init__.py:1`, `mysite/conftest.py:8`, `mysite/auth/views.py:40`, `mysite/messaging/services.py:8`) inserted repository paths before imports.
- Test harness depended on explicit pythonpath entries in `mysite/pytest.ini:7`.
- Container orchestration used `PYTHONPATH: /app` and non-standard `working_dir` values (`docker-compose.yml:49`, `docker-compose.yml:56`, `Dockerfile:13`) to make imports succeed.
- Legacy shim `mysite/audit.py:1` re-exported from `mysite.mysite.audit`, demonstrating duplicate module trees.

## Desired End State
- Single, canonical Django package (`mysite/`) that houses project settings/utilities alongside domain apps without namespace shims.
- No `sys.path` mutations at runtime; dependency resolution relies on standard interpreter behaviour or installable packages.
- Containers and local tooling start from the project root and run `python manage.py …` without custom wrappers or environment tweaks.
- Tests run with stock pytest + Django configuration (only `DJANGO_SETTINGS_MODULE` override).
- Celery/Flower continue to bootstrap from `celery -A mysite …` with `mysite.__init__` exporting `celery_app`.
- Layout aligns with Django's default project template: repo root contains `manage.py`, a single project package (`mysite/`) with settings/URL modules, and first-party apps located as siblings inside that package (or in a dedicated `apps/` subpackage) referenced via dotted paths in `INSTALLED_APPS`.

## Proposed Target Layout
```text
backend/
├── manage.py
├── mysite/
│   ├── __init__.py          # exports celery_app, no sys.path hacks
│   ├── asgi.py
│   ├── celery.py
│   ├── config/
│   │   └── settings/        # base/local/staging/test modules
│   ├── project_logging.py
│   ├── notification_utils.py
│   ├── audit.py
│   ├── apps/                # optional logical grouping for domain apps
│   │   ├── auth/
│   │   ├── keeps/
│   │   ├── messaging/
│   │   ├── emails/
│   │   └── users/
│   └── tests/
└── pyproject.toml (or setup.cfg)  # editable install to expose package when needed
```
> Note: If we keep domain apps at the top of `mysite/` instead of an `apps/` subpackage, update the plan accordingly—the key requirement is that everything lives inside the same installable package tree.

## Implementation Plan

### Phase 0 – Discovery & Decisions
- Confirm final package root name (`mysite` vs `tinybeans_backend`) and whether domain apps should sit under an `apps/` prefix.
- Inventory external consumers (scripts, management commands, CI jobs) that import from `mysite.*` or call `python -m …`.
- Document required environment variables/settings that must survive the migration.
- Decide whether to keep domain apps as direct children of the project package (matching Django's default `startapp` output) or consolidate them under `mysite/apps/` while updating `INSTALLED_APPS` accordingly.

### Phase 1 – Restructure Package Tree
- Move the inner project package (`mysite/mysite/*`) into the canonical package directory determined above.
  - Update relative imports inside moved modules (settings, celery, logging, notification utilities, tests).
  - Collapse shims such as `mysite/audit.py` once the real module lives in the correct location.
- Ensure each domain app has an `apps.py` and `__init__.py` aligned with Django conventions; relocate them under the unified package if desired.
- Update `INSTALLED_APPS` to reference the new dotted paths if they change.

### Phase 2 – Normalize Runtime Entry Points
- Rewrite `manage.py`, `mysite/__init__.py`, and any module imports to drop manual `sys.path` edits.
- Delete `sitecustomize.py` once imports succeed without it.
- Replace direct path insertion in app modules (auth, messaging) with ordinary relative or absolute imports.
- Update pytest configuration to remove the `pythonpath` block; rely on automatic discovery from the project root or `PYTHONPATH` provided by tooling.

### Phase 3 – Tooling & Container Updates
- Update `Dockerfile` and `docker-compose.yml` to use the new working directory (project root) and remove the `PYTHONPATH` override.
- Adjust container commands to run from the new structure, e.g. `command: python manage.py runserver …` without `bash -lc` if possible.
- Verify Celery/Flower commands still resolve `mysite.celery:app`.
- Ensure local developer workflow (`python manage.py`, `pytest`, `ruff`) works without additional environment tweaks.

### Phase 4 – Validation & Cleanup
- Run test suites (`pytest`, `python manage.py test --settings=mysite.test_settings`) and linting.
- Boot the stack with `docker compose up --build` to confirm services start without import errors.
- Remove orphaned files (old shim modules, empty directories) and update documentation/ADR references.
- Communicate the structural change (README, DEVELOPMENT.md) and provide migration notes for developers.

## Testing & Verification
- Automated: `pytest`, `python manage.py check`, `ruff check`, `ruff format --check`.
- Runtime: `python manage.py shell`, Celery worker startup, `docker compose up --build`.
- Smoke tests via API (e.g. authenticate, send SMS) to ensure critical paths still function.

## Open Questions
- Should we install the backend as an editable package (`pip install -e .`) inside the Docker image to guarantee availability across management commands?
- Do we want a separate `apps/` namespace to distinguish project utilities from domain apps?
- Are there external scripts or cron jobs that import using the current shimmed paths and need coordinated updates?

## Risks & Mitigations
- **Risk:** Hidden imports referencing `mysite.mysite.*` break after refactor.  
  **Mitigation:** Use `rg "mysite\\.mysite"` and run tests to surface stragglers; provide compatibility aliases only where strictly necessary.
- **Risk:** Celery or Flower entrypoints fail to resolve the application.  
  **Mitigation:** Keep `mysite/__init__.py` exporting `celery_app` and verify with `celery -A mysite inspect ping`.
- **Risk:** Developers with stale virtualenvs keep old bytecode.  
  **Mitigation:** Document cleanup steps (`find . -name '__pycache__' -exec rm -rf {}`) in rollout notes.
