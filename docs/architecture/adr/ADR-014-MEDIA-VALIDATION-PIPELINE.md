# ADR-014: Media Upload Validation, Malware Scanning, and Metadata Enforcement

## Status
**Proposed** - *Date: 2025-10-10*

---

## Context

### Background
- The keeps media pipeline currently accepts photo and video uploads via REST endpoints, persists temporary files to disk, and then triggers Celery tasks to persist originals and generate derivatives.
- Recent hardening reviews (see `docs/guides/security/django_backend_improvement_plan.md` and `docs/backend_cleanup.md`) highlighted missing defenses against malformed or malicious media, as well as duplicated storage writes and sparse observability.
- To reach OWASP ASVS L2 and Django 5.2 hardening parity before launch, we need deterministic validation, malware scanning, and richer metadata capture.

### Current State
- Validation is limited to file existence, max size checks from `settings.MAX_UPLOAD_SIZE`, and Pillow `Image.verify()` for photos (`mysite/keeps/tasks.py:162`).
- No runtime MIME sniffing occurs, so client-supplied `content_type` drives allow/deny decisions.
- Video uploads bypass structural validation; codecs, duration, and resolution are not enforced.
- Antivirus scanning is absent across the pipeline, leaving the system exposed to known malware signatures.
- Operational insights are sparse; success/failure counts, scan verdicts, and ffprobe output are not logged or exported as metrics.

### Requirements
- **Immediate**: Block malicious or malformed uploads (incorrect MIME, decompression bombs, invalid codecs), integrate antivirus scanning, ensure a single durable write per derivative, and surface actionable logs.
- **Future**: Support richer policy controls (per-circle quotas, optional AI content checks), reuse validation pipeline for future ingestion sources, and enable resumable uploads.
- **Always**: Safeguard user data, enforce consistent storage naming, maintain auditability, and keep the solution maintainable by the current Django/DevOps team.

### Constraints
- **Technical**: Must operate inside existing Docker-compose stack, rely on Celery workers, and run within current MinIO-backed storage abstraction; third-party SaaS with outbound networking may be restricted.
- **Business**: Launch timeline demands incremental delivery; cost sensitivity favors FOSS tooling where viable.
- **Organizational**: Team already manages ClamAV and ffmpeg in other services, but has limited capacity for bespoke C/C++ integrations; Python-first solutions preferred.

---

## Decision

Adopt a hardened media validation pipeline that performs MIME sniffing, Pillow safeguards, ffprobe-based video verification, and ClamAV scanning before original files enter MinIO. Failures mark uploads as `FAILED`, emit structured security logs, and clean up temporary files. Configuration is centralized in Django settings with environment overrides, and Celery tasks are refactored into composable validators to simplify testing.

### Architectural Approach

#### 1. Validation Orchestration Layer
- **Description**: Refactor `validate_media_file` into a coordinator that executes discrete validators (file existence, MIME sniff, size, media-type-specific checks, antivirus, metadata capture) and aggregates outcomes.
- **Rationale**: Modular validators promote reuse and targeted unit tests while keeping Celery task complexity manageable.
- **Implementation**: Create helper modules in `mysite/keeps/services/media_validation.py`; leverage dataclasses to pass results and raise typed exceptions that map to user-facing errors.

#### 2. Antivirus Scanning Service
- **Description**: Run a dedicated ClamAV daemon container accessible to Celery workers; stream temp files via `clamd` socket client with configurable retry/backoff.
- **Rationale**: Industry-standard virus scanning with signature updates; on-prem operation suits restricted network environments.
- **Implementation**: Add `clamav` service to `docker-compose.yml`, expose TCP socket, add `CLAMAV_HOST`, `CLAMAV_PORT`, `CLAMAV_FAIL_OPEN` settings, and implement `scan_for_malware(path)` helper using `clamd`.

#### 3. Image Hardening
- **Description**: Enforce `Image.MAX_IMAGE_PIXELS`, disallow animations (unless explicitly supported), and ensure derivative writes use deterministic hashed filenames with a single `storage.save` call.
- **Rationale**: Prevent image bombs and duplicated writes while capturing metadata (width, height, format).
- **Implementation**: Configure Pillow safeguards at import time, add `VALID_IMAGE_FORMATS`, compute hashes before save, and update `KeepMedia` to persist metadata fields.

#### 4. Video Probing and Policy Enforcement
- **Description**: Execute `ffprobe` on uploads to extract codec, duration, resolution, audio streams, and reject files outside allowlists.
- **Rationale**: Blocks incompatible or oversized videos before storage, aligns with front-end playback expectations.
- **Implementation**: Ship ffmpeg binaries in worker image, invoke via subprocess (JSON output), parse into schema, enforce `MAX_VIDEO_DURATION_SECONDS`, `MAX_VIDEO_WIDTH`, `MAX_VIDEO_HEIGHT`, `ALLOWED_VIDEO_CODECS`, and store metadata.

#### 5. Observability & Auditing
- **Description**: Emit structured logs (JSON) with scan results, create Prometheus/StatsD counters for validation outcomes, and persist validation metadata/audit details on `MediaUpload`.
- **Rationale**: Security and ops teams require visibility into blocked content and false positives.
- **Implementation**: Extend existing structlog setup (ADR-006), add metrics helpers, and augment models with `validated_at`, `validation_details` JSONField (with migration).

### Technology Selection

| Component | Technology | Version | Justification |
|-----------|------------|---------|---------------|
| Antivirus scanning | ClamAV (`clamd`) | 1.4.x daemon / 0.104+ signatures | Open-source, widely supported, Docker-friendly |
| File type sniffing | `python-magic` (libmagic) | 0.4.27 | Reliable MIME detection independent of client headers |
| Image processing | Pillow | 10.x | Already in use; supports security flags and metadata capture |
| Video probing | `ffprobe` (FFmpeg suite) | 6.x | Industry-standard metadata extraction; scriptable JSON output |
| Task queue integration | Celery | existing | Reuse current async processing with retry semantics |

### Implementation Plan

**Phase 1: Infrastructure & Configuration (1 sprint)**
- [ ] Add ClamAV container/service with health checks and update worker Dockerfile for dependencies.
- [ ] Introduce new Django settings/env vars (`CLAMAV_*`, `MEDIA_VALIDATION_*`) and document defaults.
- [ ] Publish ffmpeg binaries and ensure workers bundle them.

**Phase 2: Validation Pipeline Refactor (1–2 sprints)**
- [ ] Refactor `validate_media_file` into modular validators and add MIME sniffing + image safeguards.
- [ ] Integrate ClamAV scanning with fail-safe behavior and audit logging.
- [ ] Apply deterministic storage keys for thumbnails/gallery and persist metadata.

**Phase 3: Video Enforcement & Observability (1 sprint)**
- [ ] Implement `ffprobe` checks with codec/duration thresholds and metadata persistence.
- [ ] Add structured logging, metrics, and migrations for new audit fields.
- [ ] Expand test coverage (unit + integration) and update documentation/playbooks.

### Configuration

```python
# settings/base.py
MEDIA_VALIDATION = {
    "max_upload_bytes": env.int("MAX_UPLOAD_SIZE", default=50 * 1024 * 1024),
    "max_image_pixels": env.int("MAX_IMAGE_PIXELS", default=50_000_000),
    "allowed_image_formats": ["JPEG", "PNG", "WEBP"],
    "allowed_video_codecs": ["h264", "hevc"],
    "max_video_duration_seconds": env.int("MAX_VIDEO_DURATION_SECONDS", default=300),
    "max_video_width": env.int("MAX_VIDEO_WIDTH", default=3840),
    "max_video_height": env.int("MAX_VIDEO_HEIGHT", default=2160),
    "ffprobe_path": env.str("FFPROBE_PATH", default="/usr/bin/ffprobe"),
}

CLAMAV = {
    "host": env.str("CLAMAV_HOST", default="clamav"),
    "port": env.int("CLAMAV_PORT", default=3310),
    "timeout": env.int("CLAMAV_TIMEOUT", default=10),
    "fail_open": env.bool("CLAMAV_FAIL_OPEN", default=False),
}
```

---

## Alternatives Considered

### Alternative 1: Harden Existing Celery Pipeline (Selected)
**Description**: Keep all validation logic inside Django’s Celery workers, adding modular validators, ClamAV integration, and ffprobe checks that run asynchronously after uploads hit the API.

**Pros:**
- Minimal architectural change; reuses existing storage, models, retry semantics, and logging.
- No large binaries traverse the network—workers read temp files locally and write straight to MinIO.
- Aligns with current team expertise (Python, Celery, Pillow) and keeps a single deployment surface.

**Cons:**
- Celery workers must absorb additional CPU/memory load for scanning/probing.
- Python code handling many concerns can grow complex without careful factoring.

**Why Chosen**: Maximizes delivery speed while meeting security goals, avoids new infrastructure, and keeps validation close to storage writes so failures can block persistence.

### Alternative 2: Offload to Cloud Storage Scanning (e.g., AWS S3 + Macie/AV SaaS)
**Description**: Delegate malware scanning and media validation to cloud-native services triggered by object storage events.

**Pros:**
- Minimal maintenance; vendor handles signature updates and scaling.
- Potentially richer threat intelligence and reporting.

**Cons:**
- Requires public cloud lock-in and outbound network access not currently provisioned.
- Adds latency waiting for out-of-band scan results; complicates synchronous validation workflow.

**Why Rejected**: Conflicts with on-prem/minimal network policy and would require broader infra changes than timeline allows.

### Alternative 3: Dedicated Go Microservice
**Description**: Extract validation into a new Go service exposed over gRPC/HTTP; Django uploads call the service, which handles ClamAV/ffprobe and returns a verdict.

**Pros:**
- Potentially higher throughput and lower memory footprint per worker.
- Clear separation of concerns that could serve multiple clients or future products.

**Cons:**
- Introduces new deployment/runtime to maintain plus inter-service communication overhead and binary streaming.
- Requires cross-language tooling, new CI/CD steps, and upskilling for debugging/observability.
- Adds latency budget to synchronous checks unless paired with additional queues.

**Why Rejected**: Added operational complexity outweighs benefits for a single Django workload on current timelines.

### Alternative 4: Commercial Scanning/Mediation SaaS
**Description**: Use third-party platforms (e.g., Filestack, Cloudinary, Uploadcare) to ingest, scan, and transform media before handing back approved assets.

**Pros:**
- Outsources malware detection, media optimization, and policy enforcement to specialists.
- Rich dashboards, analytics, and optional AI moderation features.

**Cons:**
- Recurring costs and potential data residency/compliance hurdles.
- Vendor lock-in with integration churn; customization can be limited.
- Still may need custom business rules or storage integration on our side.

**Why Rejected**: Cost and control concerns plus requirement to keep user data within current infra.

### Alternative 5: Self-Hosted Gateway Filter
**Description**: Place an inline service/gateway (e.g., Envoy with WASM filters) in front of Django to intercept uploads and run validation before they reach the app.

**Pros:**
- Centralizes validation for multiple backend consumers; language-agnostic via WASM.
- Can be scaled independently from application servers.

**Cons:**
- High implementation effort; still must integrate ClamAV/ffprobe and maintain pipeline code.
- Introduces another hop and deployment artifact with its own observability/troubleshooting needs.

**Why Rejected**: Complexity and duplication of effort relative to enhancing the existing Celery workflow.

### Alternative 6: Homegrown Signature or Heuristic Scanner
**Description**: Build custom Python-based threat detection using heuristics and open signature feeds without ClamAV.

**Pros:**
- Full control over behavior; slim runtime footprint.

**Cons:**
- Significant engineering effort; high risk of poor detection accuracy and high maintenance burden.

**Why Rejected**: Recreating industry-tested antivirus capability is infeasible within scope and would expose users to avoidable risk.

---

## Consequences

### Positive Consequences
- ✅ **Improved security posture**: Malware, malformed images, and policy-violating videos are blocked before storage.
- ✅ **Operational transparency**: Structured logs and metrics enable rapid incident triage.
- ✅ **Consistent media metadata**: Downstream consumers can rely on persisted dimensions, codecs, and audit trails.

### Negative Consequences
- ⚠️ **Higher resource usage**: ClamAV and ffprobe add CPU/memory overhead to worker hosts.
- ⚠️ **Increased complexity**: Additional services and configuration knobs require operational discipline.
- ⚠️ **Potential false positives**: Strict scanning may block user uploads; support process must manage appeals.

### Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| ClamAV downtime blocks uploads | High | Medium | Configure retries, alerting, and documented fail-open toggle for emergencies |
| ffprobe missing or incompatible | Medium | Low | Bake binaries into worker image, add startup checks |
| Performance regression on large batches | Medium | Medium | Profile Celery tasks, introduce concurrency limits, and scale workers horizontally |
| False positive virus detections | Medium | Low | Log detailed scan results, provide manual override process, and maintain signature updates |

---

## Testing Strategy

### Unit Tests
- Validate MIME sniffing against known good/bad samples.
- Ensure image pixel limit, animation rejection, and metadata extraction behave as expected.
- Simulate ClamAV responses (clean, infected, connection errors).

### Integration Tests
- Use temporary files to run full validation pipeline with mocked ffprobe/ClamAV clients.
- Exercise Celery task retries and failure states, verifying `MediaUpload` status transitions.

### Performance Tests
- Benchmark average validation latency for common file sizes (5 MB photo, 100 MB video).
- Stress-test concurrent uploads to size worker pool requirements.

### Security Tests
- Scan EICAR string to confirm infection detection.
- Attempt decompression-bomb images and oversized videos to ensure rejection.

---

## Documentation Requirements

- [ ] Update `docs/guides/security/django_backend_improvement_plan.md` P1 item status once delivered.
- [ ] Add ClamAV upkeep and ffprobe troubleshooting steps to `docs/architecture/SERVICES.md`.
- [ ] Extend developer onboarding docs with new env vars and local setup instructions.
- [ ] Publish a runbook for handling blocked uploads and overrides.

---

## Monitoring and Observability

### Metrics to Track
- `media_validation_total{result="success|failure|infected|policy_block"}`: Threshold alerts on failure spikes.
- `clamav_scan_latency_seconds`: Monitor scanning performance.

### Alerts to Configure
- `MediaValidationFailureSpike`: Trigger when failure ratio >5% over 15 minutes; notify on-call security engineer.
- `ClamAVUnreachable`: Alert if scans fail consecutively for five minutes.

### Logging Requirements
- Log validation results at INFO with structured fields (`upload_id`, `mime_detected`, `clamav_verdict`, `ffprobe_codec`).
- Log errors with stack traces and correlation IDs for auditability.

---

## Success Criteria

This decision will be considered successful when:

- [ ] 100% of uploads pass through the new validation pipeline.
- [ ] Malware and policy-violating test fixtures are consistently rejected in CI.
- [ ] Observability dashboards show actionable metrics for validation outcomes.
- [ ] No new production incidents arise from unvalidated media ingress for one quarter post-launch.

**Success Metrics:**
- False positive rate <1% across 30-day sample.
- Average validation latency <2 seconds for photos, <8 seconds for 200 MB videos.

---

## Review Schedule

- **First Review**: 2026-01-15 – Assess rollout completion and operational stability.
- **Second Review**: 2026-04-15 – Evaluate false positive rate and resource usage.
- **Annual Review**: 2026-10-15 – Reassess technology choices and signature management.

---

## Related ADRs

- [ADR-001: MEDIA STORAGE ARCHITECTURE](./ADR-001-MEDIA-STORAGE-ARCHITECTURE.md)
- [ADR-006: LOGGING FRAMEWORK](./ADR-006-LOGGING-FRAMEWORK.md)
- [ADR-012: NOTIFICATION STRATEGY](./ADR-012-NOTIFICATION-STRATEGY.md)

---

## References

- `docs/guides/security/django_backend_improvement_plan.md`
- `docs/backend_cleanup.md`
- Django 5.2 hardened deployment checklist
- OWASP ASVS v4.0.3 – V8 Data Protection Requirements
- ClamAV documentation (`https://docs.clamav.net/`)
- FFmpeg `ffprobe` manual (`https://ffmpeg.org/ffprobe.html`)

---

## Approval

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Architect | TBD | - |  |
| Tech Lead | TBD | - |  |
| Product Owner | TBD | - |  |

---

## Change History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2025-10-10 | 1.0 | AI Assistant | Initial ADR creation |
