# Circles App Extraction Plan

## Objectives
- Isolate the circle domain (families, memberships, invitations, onboarding) into a dedicated Django app to clarify ownership and reduce coupling inside `mysite/users`.
- Provide a clean API surface for other apps (`keeps`, `messaging`, `auth`, `emails`) to consume circle capabilities without reaching into unrelated user internals.
- Preserve the existing database schema and public behaviour during the transition, so rollout can happen incrementally without downtime.
- Leave `mysite/users` focused on authentication, profiles, preferences, and child/pet management.

## Current State
- Models: Core circle models now live in `mysite/circles/models/` with `Meta.app_label="users"` to preserve table names. Related notification models in `mysite/users/models/notifications.py` include optional FK ties to circles.
- Serializers & views: Circle CRUD, invitation, onboarding serializers live in `mysite/circles/serializers/`, and views are split across `mysite/circles/views/`. Profile, children, and pets endpoints import circle models for permission checks.
- Signals/tasks: Invitation onboarding hooks and async tasks now live in `mysite/circles/tasks.py` and `mysite/circles/signals.py`, with legacy shims still present under `mysite/users`.
- Admin, tests, and fixtures: Admin registrations in `mysite/users/admin.py`, API tests under `mysite/users/tests/circles`, and shared pytest fixtures reference circle factories.
- Cross-app dependencies:
  - `mysite/keeps/views/comments.py` and related permissions rely on circle membership to authorize operations.
  - `mysite/messaging` services target circle roles for notifications.
  - `mysite/auth/custom_tokens.py` embeds circle membership metadata into refresh tokens.
  - Email templates (e.g., `mysite/emails/email_templates/circle_invitation_accepted.email.html`) expect circle context variables.
- Database migrations: All circle tables originate from `mysite/users/migrations/0002_*` onward. Table names use the default `users_*` prefix (e.g., `users_circle`), so moving the models will require care.

## Pain Points Today
- The `users` app has become a catch-all for both identity and collaboration features, driving large import graphs and making ownership ambiguous.
- Feature work in unrelated domains (keeps, messaging) must import from `mysite.users`, increasing the risk of circular dependencies.
- Tests and fixtures for circles intermingle with core user tests, slowing feedback cycles and complicating targeted refactors.
- Future circle-specific services (activity feeds, analytics) lack an obvious home.

## Desired End State
- A first-class `circles` Django app (`mysite/circles/`) that owns models, serializers, permissions, tasks, signals, and admin definitions for the circle domain.
- Other apps depend on `mysite.circles` for membership and invitation behaviour; `mysite.users` only references circles via well-defined interfaces.
- Database tables retain their existing names; migrations reflect the new app label without data churn.
- Circle-specific tests, fixtures, and documentation live alongside the new app.
- Public APIs remain stable (same endpoints, payloads, and URLs), minimizing client disruption.

## Proposed High-Level Architecture
```
mysite/
├── circles/
│   ├── __init__.py
│   ├── apps.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── circle.py
│   │   ├── membership.py
│   │   └── invitation.py
│   ├── permissions.py
│   ├── serializers/
│   ├── services.py
│   ├── signals.py
│   ├── tasks.py
│   ├── urls.py
│   ├── views/
│   │   ├── __init__.py
│   │   ├── circles.py
│   │   ├── invitations.py
│   │   └── memberships.py
│   └── tests/
└── users/
    ├── models/
    └── …
```
> Keep cross-app utilities (e.g., permission helpers used by `keeps`) inside `mysite/circles` to avoid back-referencing `users`.

### File Decomposition Goals
- **Models:** Split the current `circle.py` monolith into focused modules (`circle.py`, `membership.py`, `invitation.py`, enums/constants). Keep shared mixins in `models/__init__.py` or a `base.py`.
- **Views:** Break `mysite/circles/views` into smaller modules grouped by responsibility (`circles.py`, `memberships.py`, `invitations.py`, onboarding). Ensure `views/__init__.py` re-exports the public API for URL wiring.
- **Serializers:** Mirror the view decomposition so each serializer module aligns with its view namespace, improving discoverability and reducing file size.

## Implementation Plan

### Phase 0 – Preparation
1. Align on the app name (`circles`) and dotted path (`mysite.circles`). Confirm there is no existing app with that label.
2. Inventory downstream consumers relying on `mysite.users` exports:
   - Views/serializers in other apps importing `Circle`, `CircleMembership`, invitation serializers, or helper functions.
   - Signals/tasks that expect to live inside `users`.
   - Test fixtures and factory modules.
3. Decide how to expose backwards-compatible imports during migration (e.g., temporary re-export modules inside `mysite/users`).
4. Draft communication for the team including rollout expectations and any local environment steps.

### Phase 1 – Bootstrap the Circles App
1. Run `python manage.py startapp circles` (or manually scaffold) under `mysite/`.
2. Add `mysite.circles.apps.CirclesConfig` to `INSTALLED_APPS` in settings.
3. Create `__init__.py`, `apps.py`, and placeholder modules (`models/__init__.py`, `serializers/__init__.py`, etc.) to match the target layout.
4. Add a new test package `mysite/circles/tests` with `__init__.py` so the suite discovers it.

### Phase 2 – Establish Compatibility Shims
1. Move the concrete model implementations into `mysite/circles/models/{circle,membership,invitation}.py`, explicitly setting `Meta.app_label = "users"` so database tables remain unchanged during the transition.
2. Keep `mysite/users/models/circle.py` as a thin re-export layer so legacy imports continue to function while downstream modules migrate.
3. Apply the same pattern for serializers and views by introducing `mysite/circles/serializers/__init__.py` and `mysite/circles/views/{circles,invitations,memberships}.py`, with `mysite/users/serializers/__init__.py` and `mysite/users/views/circles.py` re-exporting the new implementations.
4. Update references in cross-app modules (`mysite/keeps`, `mysite/auth`, etc.) to import from `mysite.circles`. Run tests to ensure no regressions.
5. Once downstream references are updated, prune any unused direct imports from `mysite.users`.

### Phase 3 – Formalize Model Ownership
1. Generate migrations in the `circles` app using `SeparateDatabaseAndState` to associate the existing tables with the new models without touching data.
2. Update historical migrations or create deprecation shims so Django no longer expects circle models inside the `users` app.
3. Remove the re-export module once state migrations land and code references are updated.
4. Move serializers, permissions, tasks, and signals fully into `mysite/circles`, updating imports accordingly.
5. Relocate tests/fixtures to the new app, keeping shared pytest plugins updated.

### Phase 4 – Clean Up `users`
1. Remove circle-specific admin registrations from `mysite/users/admin.py` and recreate them under `mysite/circles/admin.py`.
2. Trim any residual circle utilities from `mysite/users` (e.g., services, schema definitions).
3. Ensure `mysite/users/__init__.py` no longer re-exports circle components; replace with optional deprecation shims emitting warnings if needed.
4. Update documentation (`README.md`, `DEVELOPMENT.md`) to reflect the new app boundaries.

### Phase 5 – Validation & Rollout
1. Run test suites (`pytest`, `python manage.py test --settings=mysite.test_settings`) and linting to verify the refactor.
2. Perform exploratory testing of API flows:
   - Circle creation, editing, and deletion.
   - Invitation send/accept/cancel/resend flows.
   - Membership role changes and onboarding endpoints.
3. Validate cross-app behaviours:
   - Comment creation in `keeps` respects circle permissions.
   - Auth token issuance includes correct circle IDs.
   - Email notifications render with circle data.
4. Deploy to a staging environment and monitor logs for import errors or missing signals.
5. Communicate the rollout, highlighting any deprecations and new import paths.

## Data & Migration Considerations
- Keep existing table names (`users_circle`, `users_circlemembership`, etc.) by specifying `db_table` on moved models or using `SeparateDatabaseAndState`.
- Verify foreign keys still reference the same tables; migrating app labels affects Django's ORM metadata but not the database schema if handled carefully.
- Check for fixtures or raw SQL referencing the old app label; update them to the new dotted paths.
- Ensure historical migrations remain intact. We may need to leave the original migrations under `mysite/users/migrations` but mark them as empty once the models move, or recreate canonical migrations under `circles` and squish later.

## Testing Strategy
- Automated: `pytest`, `python manage.py check`, `ruff check .`, plus any circle-specific test modules moved to the new app.
- Manual: exercise REST endpoints via Postman or automated smoke scripts, focusing on invitation acceptance and membership role enforcement.
- Regression: run Celery tasks or management commands that rely on circle invitations to guarantee signal wiring remains functional.

## Risks & Mitigations
- **Risk:** Django perceives model moves as table drops/creates.  
  **Mitigation:** Use `SeparateDatabaseAndState` migrations with explicit `db_table` to preserve data.
- **Risk:** Downstream imports forget to update to `mysite.circles`, causing runtime errors.  
  **Mitigation:** Grep for `mysite.users.*Circle` usage and add temporary compatibility exports with `DeprecationWarning`.
- **Risk:** Signals/tasks fail after relocation if import paths change.  
  **Mitigation:** Ensure the `ready()` method of `CirclesConfig` wires signals; double-check Celery beat schedules and task names.
- **Risk:** Tests rely on fixtures located under `mysite/users/tests`.  
  **Mitigation:** Move fixtures with the tests and update `pytest_plugins` entries; run the suite to surface missing imports.

## Open Questions
- Do we want to rename database tables to `circles_*` eventually, or is the current naming acceptable?
- Should invitation and onboarding workflows remain within the same app, or should onboarding move to a dedicated domain later?
- Are there API versioning considerations if we expose new endpoints under a different namespace?
- How long should compatibility shims in `mysite/users` remain before removal?

## Rollout Checklist
- [x] Code scaffolding created (`mysite/circles` app, INSTALLED_APPS updated).
- [x] Compatibility shims verified and downstream imports switched.
- [ ] Models, serializers, views, signals, tasks migrated.
- [ ] Admin, fixtures, and tests relocated.
- [ ] Migrations generated and reviewed for data safety.
- [ ] Automated and manual testing completed.
- [ ] Documentation updated, rollout announcement shared.
- [ ] Compatibility shims scheduled for removal (track in issue board).
