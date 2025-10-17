# Backend Logging & Audit Trail Overhaul

## Overview
The backend currently relies on Django’s default logging with limited structured data and inconsistent instrumentation across apps. This initiative delivers a cohesive logging architecture that supports debugging, operational visibility, and security/audit requirements without leaking sensitive information.

## Goals
- Provide structured, queryable logs for all critical backend flows.
- Capture contextual metadata (trace IDs, user/session IDs, request info) across synchronous and async workloads.
- Standardize log levels and message shapes to reduce noise and accelerate triage.
- Emit dedicated audit/security events for authentication, authorization, and data access boundaries.
- Ensure logging remains safe for PII/PHI and complies with retention requirements.

## Non-Goals
- Replacing the existing monitoring stack (metrics, tracing) beyond log integrations.
- Building a bespoke SIEM or log analysis UI.
- Refactoring business logic outside of adding instrumentation hooks.

## Stakeholders
- Engineering (backend, infra, SRE) – implementation and maintenance.
- Security/Compliance – define audit requirements and review retention/redaction policies.
- Support & Ops – consume enriched logs for incident response.

## Requirements
1. **Configuration**
   - Centralize logging configuration under `mysite/logging.py` and load from settings.
   - Enable JSON-formatted logs with level, timestamp, logger, message, and context payload.
   - Support environment-driven toggles (log level, handler destinations).
2. **Context Propagation**
   - Middleware to inject request ID and user/session context into log records.
   - Celery task wrapper to propagate correlation IDs across async boundaries.
   - Utilities to add domain-specific context (e.g., circle_id, message_id).
3. **Audit & Security Logging**
   - Define taxonomy for audit events (login, permission change, data export, admin actions).
   - Provide helper functions to emit audit logs with severity and actor/target metadata.
   - Ensure security logs are segregated for stricter retention and access control.
4. **Instrumentation**
   - Add structured logs to key entry points in `users`, `messaging`, and `keeps` apps (views, services, Celery tasks).
   - Capture failures, retries, external API interactions, and state transitions.
   - Avoid logging secrets, passwords, tokens, and raw PII.
5. **Operational Readiness**
   - Update docs (`docs/guides/logging.md` or similar) with usage guidelines and examples.
   - Provide smoke tests verifying instrumentation (e.g., log capture in pytest).
   - Ensure compatibility with Docker stack and existing log shipping (stdout).

## Architecture & Design
- **Logging Configuration Module**: Create `mysite/logging.py` encapsulating formatters, handlers, filters, and loggers. Import in `settings.py` via `LOGGING = get_logging_config(environment_variables)`.
- **Structured Formatter**: Implement JSON formatter (standard library or `python-json-logger`) outputting ISO timestamps, log level, logger name, message, and context dict.
- **Handlers**: Default to console handler (stdout). Permit optional file handler and external aggregator (e.g., ELK, Datadog) via environment settings.
- **Filters & Context**: Implement `RequestContextFilter` to enrich records with trace IDs, user IDs, IP addresses. Use Django middleware to generate/attach `request_id` header if absent.
- **Audit Logger**: Configure dedicated logger `mysite.audit` routing to separate handler with stricter level and retention toggles.
- **Celery Integration**: Wrap tasks with decorator or base task class injecting correlation IDs and task metadata into the logging context.

## Implementation Plan
1. **Configuration Foundation**
   - Add `mysite/logging.py` with helper API and unit tests.
   - Update `mysite/settings.py` (all env variants) to consume the new logging config.
2. **Context Middleware & Utilities**
   - Implement `RequestContextMiddleware` adding request IDs (via `uuid4`) and user info.
   - Extend existing Celery base task or add mixin for context propagation.
   - Introduce helper functions for adding contextual fields without leaking PII.
3. **Audit Logging Helpers**
   - Define `AuditEvent` dataclass or helper in `mysite/audit.py`.
   - Provide convenience functions for common events (login success/failure, permission changes).
   - Document schema for audit events (actor, subject, action, severity, metadata).
4. **App Instrumentation**
   - Audit `users/`, `messaging/`, `keeps/` for critical flows; add logs at major state changes, error paths, external calls.
   - Ensure Celery tasks and signal handlers emit start, success, failure logs with context.
   - Add targeted logging to security-sensitive operations (role updates, data exports).
5. **Testing & Validation**
   - Add pytest fixtures to capture logs and assert presence/shape for new instrumentation.
   - Update existing tests where necessary to account for injected middleware/context.
   - Run `pytest` and `ruff` to confirm compliance.
6. **Documentation & Rollout**
   - Create/Update logging guide detailing usage patterns, log levels, audit event types, and anti-patterns.
   - Coordinate with DevOps to confirm log shipping pipeline supports JSON payloads and audit stream.
   - Monitor staging rollout, adjust log levels and sampling to balance verbosity vs. signal.

## Security & Compliance Considerations
- Enforce redaction helpers for sensitive fields before logging.
- Validate that audit logs contain sufficient detail (actor, target, timestamp, outcome) for compliance reviews.
- Coordinate with security on retention policies; ensure audit logs route to restricted storage.
- Add guardrails (lint rule or helper) discouraging direct string interpolation of user-provided data into logs.

## Risks & Mitigations
- **Log Noise**: Establish review pass to keep logs actionable; allow per-module level overrides.
- **Performance Overhead**: Benchmark middleware and JSON formatting; consider async handlers if latency rises.
- **PII Leakage**: Implement redaction utilities, code review checklist, and possibly automated tests scanning for forbidden keys.
- **Integration with Existing Infrastructure**: Collaborate with DevOps early to adapt shipping/aggregation pipelines.

## Dependencies & Open Questions
- Confirm availability or install plan for JSON logging library (`python-json-logger` or similar).
- Align on correlation ID format (UUID vs. ULID) and whether to reuse existing tracing headers.
- Decide whether to integrate with request tracing (OpenTelemetry) for combined logs/traces.
- Determine audit log retention schedule and access controls with security/compliance teams.

