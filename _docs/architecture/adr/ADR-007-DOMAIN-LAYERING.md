# ADR-007: Domain Layering Strategy for Django Services

## Status
**Proposed** - *Date: 2025-10-02*

## Context
Tinybeans runs a Django monolith with REST endpoints, Celery workers, and background jobs that all rely on the same ORM models. Django's idiomatic "fat model" pattern encourages placing business rules, query helpers, and persistence logic together on the model classes themselves. Over time, this has produced tightly coupled code that is difficult to unit test, expensive to refactor, and risky to scale across teams.

### Pain Points Observed
- Model methods blend validation, side effects, outbound integrations, and persistence in one place, making behavior hard to reason about.
- Re-using domain logic outside of Django (e.g., async workers, scripts, potential microservices) currently requires bootstrapping the entire ORM or duplicating code.
- Tests must hit the database because the logic depends on ORM internals, slowing feedback loops and complicating test data management.
- Developers hesitate to change core model methods, fearing cascading regressions or data corruption in production.

### Constraints
- Existing Django models define schema, validation, and admin behavior; replacing them wholesale is not feasible in the short term.
- Teams ship features incrementally and need an approach that allows gradual adoption without large-bang rewrites.
- Migrations and admin interfaces depend on ORM models remaining the source of truth for persistence metadata.

## Decision
Adopt an explicit **Service → Repository → Model layering** for domain logic, using Django ORM models strictly as persistence adapters.

### Key Elements
1. **Domain Services** encapsulate business workflows, orchestration, and invariants. They depend on repositories and value objects rather than direct ORM calls.
2. **Repositories** expose a narrow interface per aggregate (e.g., `FamilyRepository`, `MediaRepository`) and are the only layer allowed to talk to Django ORM models. They return domain models or value objects, not ORM instances.
3. **Domain Models** capture state and behavior that is independent of persistence concerns. Django ORM models remain the persistence schema, while lightweight domain models (plain dataclasses or Pydantic types) express business concepts without ORM coupling.
4. **Application Boundaries** (REST views, GraphQL resolvers, Celery tasks) invoke domain services and never reach into repositories or models directly.
5. **Validation** is split: persistence validation (field constraints) stays on ORM models; business rules move to services or dedicated validators operating on domain models.

### Incremental Adoption Pattern
- For legacy areas, introduce repositories that wrap existing query logic, then extract business methods from models into services one use case at a time.
- For new features, start with service + repository scaffolding and keep models thin (schema-only).
- Add thin facades around Django signals or admin hooks to call services instead of embedding logic inline.

## Consequences

### Benefits
- Business logic is context-aware, testable, and reusable without the ORM or HTTP stack, while still aligning with Django's "model" terminology.
- Clear ownership boundaries help larger teams work in parallel without stepping on each other’s toes.
- Infrastructure concerns (transactions, caching, retries) can be centralized inside repositories and services instead of scattered across models.
- Future migrations to modularized services or event-driven workflows require less untangling.

### Trade-offs / Costs
- More boilerplate: each feature requires service/repository wiring, and developers must learn the layering conventions.
- Debugging adds indirection because data now flows through adapters before hitting the database.
- Existing rich model APIs (e.g., querysets custom methods) may need wrappers or rewriting, increasing short-term effort.

## Alternatives Considered
- **Status quo (fat Django models):** Familiar and compact, but perpetuates tight coupling, hard-to-test logic, and hinders non-HTTP use cases.
- **Domain logic in QuerySets/Managers:** Improves reuse for queries but retains coupling to ORM and keeps business rules near persistence concerns.
- **Full Domain-Driven Design with aggregates and repositories per aggregate root:** Offers strong boundaries but would demand a ground-up refactor that outpaces current team capacity.

## Implementation Notes
- Establish coding conventions (`DOMAIN/services/*.py`, `DOMAIN/repositories/*.py`, `DOMAIN/models/*.py`) and enforce via linting or cookiecutter templates.
- Introduce interface definitions (via `Protocol` classes) to allow dependency inversion and easier unit-test doubles.
- Update onboarding and contribution guides so new features default to the layered approach.
- Provide migration playbooks for moving existing Django model methods into services, including test patterns (e.g., using in-memory repositories) and guidance on creating corresponding domain models.

## Open Questions
- What infrastructure is needed to manage transactions spanning multiple repositories (e.g., unit-of-work abstraction)?
- Should repositories return Django model instances for backward compatibility during transition, or immediately emit pure domain models?
- How will caching and read replicas integrate with the repository layer without reintroducing hidden coupling?

## Decision Drivers
- Maintainability and team scalability over the next 12–18 months.
- Reduced production risk by isolating side effects and persistence.
- Consistent layering across HTTP endpoints, background jobs, and future services.

## Follow-Up Actions
1. Draft a reference implementation (service, repository, domain model) for a high-impact domain (e.g., media uploads) to validate ergonomics.
2. Update developer documentation (`DEVELOPMENT.md`, `docs/guides`) with layering standards and examples.
3. Add checks (code review templates, lint rules) to prevent new business logic from landing directly on models.
