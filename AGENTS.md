# Repository Guidelines

## Project Structure & Module Organization
- Backend Django project lives in `mysite/` with domain apps (`users/`, `messaging/`, `keeps/`, etc.) and `manage.py` at the root. Tests sit beside code; shared fixtures and settings live in `mysite/pytest.ini`.
- Frontend React/TypeScript client lives in `web/` (Vite + TanStack Router); UI components sit under `web/src/` and design tokens in `web/components.json`.
- Docs and ADRs sit in `docs/`. Docker assets (`Dockerfile`, `docker-compose.yml`) define the local stack with Postgres, Redis, Celery, and the web app.

## Build, Test, and Development Commands
- `docker compose up --build`: boot API, workers, frontend with migrations and demo data.
- `docker compose exec web python manage.py migrate`: apply schema changes inside the container.
- `python manage.py test --settings=mysite.test_settings` or `pytest`: run backend tests; both use the lightweight test settings.
- `npm install && npm run start` (in `web/`): start the React client via the Vite dev server.
- `npm run build` (in `web/`): create a production bundle.
- `ruff check .` and `ruff format .`: lint and format backend code; `npm run lint` / `npm run format` run Biome for the frontend.

## Coding Style & Naming Conventions
- Python code follows PEP 8 with 4-space indentation; use descriptive module names (snake_case) and class names (PascalCase). Keep reusable logic in app-level `services.py` or `tasks.py`.
- Frontend modules follow TypeScript strict mode; keep React components PascalCase and custom hooks named `useX`. Organize UI under `web/src/components/` and co-locate tests with implementation.
- Commit only formatted code; run Ruff and Biome scripts before pushing.

## Testing Guidelines
- Follow `pytest.ini` conventions: files `test_*.py` or `*_tests.py`, classes named `Test*`, functions `test_*`.
- Favor deterministic, isolated tests that rely on `mysite.test_settings`; use the in-memory cache and broker provided there.
- Frontend specs run with Vitest via `npm run test`; colocate `.test.tsx` files alongside components.

## Commit & Pull Request Guidelines
- History shows terse commits; prefer imperative subjects (`Add circle invite model`) with bodies summarizing intent and context.
- Each PR should summarize scope, list backend/frontend touchpoints, note migrations or new env vars, and include test commands executed.
- Link relevant issues and attach UI screenshots or API samples when behavior changes.

## Environment & Secrets
- Copy `.env.example` to `.env` for the backend and `web/.env.local` for frontend overrides; never commit real credentials.
- For Google OAuth flows, follow `DEVELOPMENT.md` to register client IDs and update redirect URIs before testing.
