# ADR-006: Logging Framework Strategy for Tinybeans

## Status
**Proposed** - *Date: 2025-10-02*

## Context
Tinybeans spans a Django REST API, asynchronous workers, a React frontend, and third-party integrations. The current logging approach mixes unstructured print statements, container stdout, and ad-hoc tracing, which makes root-cause analysis slow and inconsistent across environments.

### Observability Goals
- Emit structured, contextual logs from every runtime (web, worker, and frontend consoles where feasible)
- Enrich logs with correlation identifiers (request IDs, family IDs, user IDs) to tie events across services
- Support local-first workflows via Docker Compose without depending on SaaS credentials
- Allow production and staging to stream logs to one or more managed observability providers without code changes
- Provide retention controls, Personally Identifiable Information (PII) handling, and export capabilities for compliance requests

### Constraints
- Backend services run in containers in all environments; local developers rely on Docker Compose
- Existing infrastructure already ships metrics via Prometheus and traces via OpenTelemetry SDKs
- Network egress from production is locked down; outbound integrations must use TLS and static endpoints
- Cost is a material consideration; Tinybeans wants optionality between self-hosted OSS and commercial SaaS

## Decision
Adopt an **OpenTelemetry-first logging pipeline** that produces structured JSON logs in code, forwards them directly to a shared OpenTelemetry Collector (OTel Collector) in every environment, and routes those logs to downstream providers (Grafana Loki locally; Datadog or AWS CloudWatch in production).

### Key Elements
1. **Application Instrumentation**
   - Python services use `structlog` with OpenTelemetry log exporters, injecting trace/span IDs and domain context.
   - Node-based tooling (if any) uses `pino` or `winston` with the OTLP exporter; frontend uses browser console shipping only for critical events via HTTP collector.
   - Logging configuration driven by environment variables (`LOG_LEVEL`, `LOG_FORMAT`, `OTEL_EXPORTER_ENDPOINT`).

2. **Collector Layer**
   - Shared OpenTelemetry Collector instances receive OTLP (HTTP/gRPC) log exports and container stdout (via the `filelog` receiver), applying processors (redaction, sampling, attribute mapping) before routing.
   - Collector pipelines map logs to environment-specific exporters (Loki, Datadog, CloudWatch) without additional hop services.

3. **Local Developer Experience**
   - Extend `docker-compose.yml` with `otel-collector`, `grafana`, and `loki` services to form a self-contained logging stack.
   - Developers view logs in Grafana Explore and can export JSON; no external credentials needed.
   - Optional `make logs` helper streams formatted results from the collector for quick CLI inspection.

4. **Production Targets**
   - Support Datadog and AWS CloudWatch as first-class managed sinks, selectable via environment flag (for example `LOG_DESTINATION=datadog|cloudwatch`). Collector exporters (Datadog OTLP HTTP, AWS CloudWatch Logs) handle the final delivery.
   - Maintain a nightly batch export to object storage (S3) for long-term retention and compliance.
   - Keep other SaaS providers (Elastic, New Relic, Loggly) as optional future destinations via additional environment-driven routing rules.

## Architecture Overview
```
┌──────────────────────────┐        ┌───────────────────────────┐
│   Application Services   │        │     Frontend Clients      │
│ (Django API, Celery, etc.)│       │ (Browser, Mobile Bridge) │
└──────────────┬───────────┘        └──────────────┬────────────┘
               │ OTLP / STDOUT / HTTP                              
               ▼                                                
        ┌──────────────────────┐                                
        │ OpenTelemetry Collector│                              
        │  • Receivers (OTLP, filelog) │                         
        │  • Attribute processors      │                         
        │  • Redaction / sampling      │                         
        │  • Exporters (sink routing)  │                         
        └────────────┬─────────┘                                
                     │                                           
      ┌──────────────┼──────────────────────────────┐          
      │              │                              │          
┌────────────┐ ┌───────────────┐            ┌────────────────┐
│ Grafana    │ │ Object Storage │            │ SaaS Providers │
│ Loki (Dev) │ │ (S3 archival)  │            │ (Datadog, etc.)│
└────────────┘ └───────────────┘            └────────────────┘
```

## Evaluated Providers and Integrations
| Provider / Stack | Strengths | Weaknesses | Recommended Usage |
| --- | --- | --- | --- |
| **Grafana Loki (self-hosted)** | Tight Grafana integration; cost-effective for high-volume logs; labels align with Prometheus; easy Docker Compose setup | Requires managing storage/retention; query language (LogQL) learning curve; scaling needs DynamoDB/S3 or boltdb-shipper tuning | Primary local dev target; optional production use for cost-sensitive workloads |
| **Elastic Stack (Elastic Cloud or self-hosted)** | Mature ecosystem; powerful search/analysis; Beats/Agent integrations; alerting | Operational overhead (if self-hosted); licensing complexity; requires JVM tuning | Consider for teams already invested in Elastic; strong compliance and audit scenarios |
| **Datadog Logs** | Unified metrics, traces, logs; built-in log pipelines, security rules, anomaly detection; native OTLP HTTP/gRPC endpoints | Premium pricing at high ingest; vendor lock-in; sampling required to control costs | Primary managed destination for production (`LOG_DESTINATION=datadog`); minimal operational overhead |
| **New Relic Logs** | Simple OTLP ingestion; good alerting; pricing includes other telemetry; AI-assisted diagnostics | Less mature UI vs. Datadog; retention tiers limited; advanced correlation may require NR agents | Fits teams already on New Relic One; mid-tier pricing with bundled telemetry |
| **Loggly (SolarWinds)** | Straightforward setup; competitive pricing; good for classic syslog/JSON logs | Less advanced correlation/tracing; UI dated; limited enterprise security/compliance features | Lightweight SaaS option for smaller teams; fallback or secondary target |
| **AWS CloudWatch Logs** | Native to AWS; integrates with IAM/KMS; supports OTLP-to-Firehose/CloudWatch integration via OTel exporter | Query UX weaker; cross-account sharing tricky; requires regional configuration per account | Default compliance-focused destination (`LOG_DESTINATION=cloudwatch`); leverages existing AWS controls |

## Pros and Cons Summary
**Pros**
- OpenTelemetry provides vendor-neutral log schema and supports traces/metrics correlation.
- Collector pattern centralizes redaction, sampling, and routing logic without touching application code.
- Local Loki stack delivers fast feedback and mirrors production pipeline behavior.
- SaaS connectors keep future migrations low-risk; only configuration changes are needed.

**Cons / Risks**
- Additional infrastructure (collector, Loki) increases local resource usage.
- Team must standardize on structured logging conventions; migration effort required for legacy code paths.
- Collector misconfiguration could drop or leak logs; needs automated testing and monitoring.
- Multiple destinations raise cost observability; require budgets and rate limiting.

## Implementation Plan
1. **Foundations (Sprint 1)**
   - Add `structlog` (backend) and OpenTelemetry logging exporter dependencies.
   - Define logging schema contract (levels, required attributes, PI rules).
   - Provide a shared collector configuration (`collector.yaml`) with receivers for OTLP and container file logs, plus Loki exporter for local dev.
   - Update Docker Compose with `otel-collector`, `loki`, `grafana` containers and default `LOG_DESTINATION=local`.

2. **Pipeline Hardening (Sprint 2-3)**
   - Configure collector processors (batching, attributes, redaction, tail sampling) and exporters for Datadog/CloudWatch.
   - Instrument Celery workers, request middleware, and frontend gateway for correlation IDs.
   - Build CI smoke tests validating log emission via ephemeral collector stack.

3. **Production Rollout (Sprint 4+)**
   - Extend collector configuration to support Datadog and CloudWatch exporters, routing based on `LOG_DESTINATION` (env flag) with optional fan-out for multi-sink scenarios.
   - Validate buffering/backpressure settings for OTLP exporters and ensure retries/queue limits match SLAs.
   - Wire secrets (API keys, endpoints, AWS credentials) via environment configs and secrets manager (no Terraform dependency).
   - Enable S3 archival sink and retention policies; document runbooks and failure modes.

4. **Continuous Improvement**
   - Add alerting on collector queue depth and exporter failures.
   - Train developers on LogQL/Log Search practices.
   - Periodically review ingestion costs and adjust sampling strategies.

## Logging Coverage Audit
- **Authentication Flow Updates** (`mysite/auth/views.py`): instrument login, signup, password reset/change, token refresh, logout, and email verification endpoints with structured logs capturing anonymized user identifiers, request metadata, and branch outcomes (e.g., 2FA required, rate-limited, invalid token).
- **Two-Factor Authentication Lifecycle** (`mysite/auth/views_2fa.py`, `mysite/auth/services/twofa_service.py`, `mysite/auth/services/trusted_device_service.py`): ensure every setup/verification/disable event, recovery-code usage, trusted-device mutation, and OTP verification failure emits structured logs aligned with existing `TwoFactorAuditLog` records, including success flags, methods, IPs, and device identifiers.
- **Circle Management Activities** (`mysite/circles/views/`): add info/warn logs around circle creation, updates, invitation issuance/acceptance, membership changes, and permission denials to surface collaboration workflow issues and security probes.
- **Profile & Notification Preferences** (`mysite/users/views/profile.py`): log profile edits and email preference changes with user and circle context to aid debugging of personalization issues.
- **Media & Comment Workflows** (`mysite/keeps/views/upload_views.py`, `mysite/keeps/views/media.py`, `mysite/keeps/views/comments.py`): track upload validations, async processing kickoff, unauthorized access attempts, and comment moderation actions with keep/circle identifiers and sanitized file metadata.
- **Token Utilities** (`mysite/auth/token_utils.py`): log cache operations (store/pop/delete) and cookie writes/clears with correlation IDs to diagnose token replay and cookie configuration errors.
- Apply ADR‑006 logging schema (JSON fields for `request_id`, `user_id`, `circle_id`, `keep_id`, `auth_context`, `outcome`) and avoid leaking secrets/PII while preserving enough context for downstream Datadog/CloudWatch analysis.

## Consequences
- **Positive**: Unified logging improves MTTR, compliance response, and developer experience; easier cross-environment debugging.
- **Negative**: Requires ongoing ownership (logging guild or SRE) to maintain collectors, schemas, and budgets; introduces new failure domain.
- **Neutral**: Existing third-party SDK logs must be wrapped or filtered; may expose noisy libraries needing configuration.

## Further Research
- Evaluate Grafana Alloy (successor to Agent) as an alternative to Vector for log shipping.
- Prototype sensitive-field redaction rules using OpenTelemetry `transform` processor.
- Investigate browser log sampling strategies to control client-side volume.
- Assess cost forecasts for Datadog vs. Elastic Cloud using projected daily log volume.
