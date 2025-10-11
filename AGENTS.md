# Repository Guidelines

## Project Structure & Module Organization
Backend code lives under `mysite/`, with domain apps such as `users/`, `messaging/`, and `keeps/`. Each app keeps its tests beside implementation files, and shared fixtures reside in `mysite/pytest.ini`. The React client sits in `web/`, with components in `web/src/` and design tokens centralized in `web/components.json`. Docs and architectural notes live in `docs/`, while Docker assets (`Dockerfile`, `docker-compose.yml`) define the Postgres/Redis/Celery stack.

## Build, Test, and Development Commands
Use `docker compose up --build` to boot the full stack with migrations and demo data. Apply schema updates via `docker compose exec web python manage.py migrate`. Run backend tests with `python manage.py test --settings=mysite.test_settings` or `pytest`. For frontend work, run `npm install && npm run start` from `web/`, then build with `npm run build`. Lint and format Python using `ruff check .` and `ruff format .`; lint and format the frontend with `npm run lint` and `npm run format`.

## Coding Style & Naming Conventions
Follow PEP 8 with 4-space indentation. Modules stay in snake_case, classes in PascalCase, and shared business logic belongs in each app’s `services.py` or `tasks.py`. TypeScript runs in strict mode: React components use PascalCase, custom hooks start with `use`, and UI elements live in `web/src/components/` alongside their styles and tests. Keep identifiers descriptive and avoid abbreviations unless already established.

## Testing Guidelines
Backend tests rely on pytest with files named `test_*.py` or `*_tests.py`, classes prefixed `Test`, and functions `test_*`. Point tests at the lightweight settings via `mysite.test_settings` to benefit from the in-memory cache and broker. Aim for deterministic, isolated scenarios and favor shared fixtures when reusing setup. Frontend specs use Vitest; run them with `npm run test` and colocate `.test.tsx` files with the corresponding component.

## Commit & Pull Request Guidelines
Commit messages stay short, imperative, and descriptive, e.g., `Add circle invite model`. Squash incidental noise before committing, and keep code formatted. Pull requests summarize scope, call out backend and frontend touchpoints, mention migrations or new environment variables, and list the commands executed for verification. Link related issues and attach screenshots or API samples when behavior changes to streamline review.

## Security & Configuration Tips
Copy `.env.example` into `.env` for backend settings and `web/.env.local` for frontend overrides before local work. Never commit real credentials, API keys, or cloud secrets. Follow `DEVELOPMENT.md` for configuring Google OAuth client IDs and redirect URIs, and rotate tokens promptly if they leak.
