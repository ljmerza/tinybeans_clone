# Notification Strategy Implementation Epics

This document summarizes the high-level epics required to implement ADR-012 (Notification Strategy: Standardized Backend Messages & Frontend Presentation Control).

## Goals
- Eliminate duplicate / conflicting user messages
- Standardize backend message schema (`messages[]`) across all endpoints
- Establish robust i18n foundation and dynamic language selection
- Give frontend explicit control of presentation channels (toast, inline, modal, silent)
- Add quality gates to prevent untranslated keys or schema drift
- Provide safe, observable rollout & monitoring

## Success Metrics (mapped from ADR)
| Metric | Target |
|--------|--------|
| Duplicate toast occurrences in key flows | 0 after full rollout |
| Missing translation key errors (prod, 30d) | 0 |
| New endpoints using standardized schema | 100% |
| Additional language enablement steps | Locale files only (no code) |
| Form validation errors rendered inline | 100% migrated forms |

## Epic Overview
| Epic ID | Name | Primary Outcome | Duration (est.) |
|---------|------|-----------------|-----------------|
| NS-001 | Backend Message Schema & User Language Field | Unified response pattern + `language` field | 1 wk |
| NS-002 | Frontend i18n Foundation | i18n config, locale files, language switching | 1 wk (parallel) |
| NS-003 | Endpoint Migration (Wave 1 & 2) | Top 80% traffic endpoints migrated | 2 wks |
| NS-004 | Frontend Message Handling Refactor | Removal of auto-toast + new utilities | 1 wk (overlaps NS-003) |
| NS-005 | Quality Gates & Tooling | CI checks, key audit, linting guardrails | 1 wk |
| NS-006 | Rollout, Monitoring & Hardening | Progressive enablement + metrics | 1 wk |

Total calendar span (with overlap): ~5 weeks.

---

## NS-001: Backend Message Schema & User Language Field
**Objectives**
- Introduce `messages[]` structure (serializer / response builder helper)
- Add `language` enum field to User model (migration + API exposure)
- Remove legacy `default_message`, `level`, `channel` in new code paths
- Add OpenAPI shared component schema for `MessageItem`

**Key Deliverables**
- `MessageBuilder`/helper function (flat context validation)
- DB migration & model update for user language
- Documentation in backend README / OpenAPI

**Acceptance Criteria**
- Sample endpoint (e.g., profile photo upload) returns new format
- OpenAPI spec shows `messages` schema once (ref) reused
- User can set language preference via API

## NS-002: Frontend i18n Foundation
**Objectives**
- Create `src/i18n/` config (react-i18next)
- Add base `en` + `es` resource bundles (extendable)
- Implement dynamic `i18next.changeLanguage(user.language)` after auth/profile load
- Provide developer docs on key naming conventions & interpolation

**Key Deliverables**
- `i18n/config.ts`, `locales/{en,es}.json`
- Language switch hook / utility
- Storybook (if present) decorator for language switching (optional stretch)

**Acceptance Criteria**
- App re-renders translated content when user language changes without reload
- Fallback behavior shows English for missing keys

## NS-003: Endpoint Migration (Wave 1 & 2)
**Objectives**
- Convert existing endpoints to emit standardized `messages` only when necessary
- Remove legacy message fields & auto-generated strings

**Wave Planning**
- Wave 1 (High Traffic / User-Facing): Auth, Profile, Media Upload, Password Reset
- Wave 2 (Remaining CRUD / Settings / Misc. operations)

**Key Deliverables**
- Migration checklist per endpoint
- Changelog noting removed fields

**Acceptance Criteria**
- 80% of requests (based on access logs) use new schema after Wave 1
- 100% endpoints migrated by end of Wave 2
- No regression in API error handling tests

## NS-004: Frontend Message Handling Refactor
**Objectives**
- Remove automatic toast side-effects from shared HTTP client/interceptor
- Implement message utilities: `deriveSeverity(status)`, `batchMessages(messages, t)`
- Update feature hooks/components (Auth, Profile, Upload, Forms) to explicitly decide channel

**Key Deliverables**
- `lib/notifications/` (or similar) utilities module
- Updated hooks with explicit message mapping
- Documentation: “When to show a toast vs inline vs none”

**Acceptance Criteria**
- No global automatic toasts triggered in migrated flows
- Validation errors appear inline per field when `context.field` present
- Background tasks show batched toasts (if opted-in)

## NS-005: Quality Gates & Tooling
**Objectives**
- Prevent missing translation keys & nested contexts
- Enforce consistent usage in CI

**Tooling**
- Script to scan code for `i18n_key` literals emitted by backend & verify keys in locale JSON
- ESLint rule or custom check to forbid direct user-facing English strings in API message emission paths
- Unit tests for `MessageBuilder` (reject nested context)

**Acceptance Criteria**
- CI fails if unknown translation key detected
- CI fails if context object is nested (unit test coverage)
- Dev guide updated with troubleshooting section

## NS-006: Rollout, Monitoring & Hardening
**Objectives**
- Progressive enablement (feature flag / percentage or endpoint toggles)
- Add logging for unknown keys during initial 2 weeks
- Dashboard / queries: frequency of `messages[]` usage, missing key logs
- Post-rollout cleanup of temporary logs / flags

**Acceptance Criteria**
- 0 unknown translation key warnings after monitoring window
- Feature flag removed / always-on
- Runbook documented (adding new message key workflow)

---

## Cross-Epic Dependencies
| Depends On | Blocked Epics |
|------------|---------------|
| NS-001 | NS-003, NS-006 |
| NS-002 | NS-004, NS-005, NS-006 |
| NS-003 | NS-006 (for full rollout metrics) |
| NS-004 | NS-006 |
| NS-005 | NS-006 |

## Risk Mitigation Summary
| Risk | Mitigation |
|------|------------|
| Inconsistent partial rollout behavior | Endpoint-level feature flag gating new schema |
| Missed endpoints | Inventory audit script comparing route list vs migrated list |
| Developer reintroduces auto-toast | Lint rule + code review checklist |
| Translation drift | CI diff check on locale files + key audit script |

## Communication Plan
- Weekly status update in engineering sync (migration % + incidents)
- #dev channel summary after each wave
- Post-mortem / retrospective after full rollout (attach metrics)

## Rollback Strategy
- Keep legacy message fields behind temporary flag for first 2 weeks (off by default)
- Re-enable legacy emission only if critical UX regression discovered (time-boxed)
- Remove rollback code after hardening (target: end of NS-006)

## Developer Quick Start (TL;DR)
1. Add new backend message: use `i18n_key` + flat `context`; do NOT embed English string
2. Add corresponding locale entries (en + other languages)
3. Frontend: translate via `t(key, context)` and decide channel explicitly
4. If validation: include `field` in context for inline mapping

---

## Open Questions
| Question | Owner | Resolution Target |
|----------|-------|-------------------|
| Do we support pluralization in first iteration? | FE Lead | Before NS-002 end |
| Include message codes separate from i18n_key? | BE Lead | If needed pre-NS-003 |
| Add telemetry tag for each message key? | Platform | During NS-006 |

---

## References
- ADR-012 Notification Strategy
- ADR-011 Frontend File Architecture (for placement of utilities)
