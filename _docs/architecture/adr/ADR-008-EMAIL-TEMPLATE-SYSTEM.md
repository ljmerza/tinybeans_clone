# ADR-008: Django Template-Based Email Rendering

## Status
**Proposed** - *Date: 2025-10-02*

## Context
Emails are currently defined as Python functions in `mysite/emails/templates.py` that return hard-coded subject/body tuples. This approach prevents non-developers from editing copy, discourages HTML layouts, and makes localization difficult. We recently introduced a Service → Repository → Model layering for email dispatch, which offers a clean seam for improving the template pipeline.

### Pain Points
- Plain strings prevent rich HTML styling, preview tooling, or designer workflows.
- Template logic and registration live in code, so copy changes require deployments.
- Unit tests around inline strings provide limited confidence for production rendering.
- Adding localization or multi-variant content would multiply inline functions, increasing risk.

### Constraints
- We must keep the existing `send_email_task` contract and Celery workflow intact.
- The system should work in Docker/Django without extra runtime services.
- Template discovery must not slow application startup significantly.
- Short-term migration effort should be manageable for the current email set (verification, password reset, invitations, child upgrade).

## Decision
Adopt Django's built-in template engine for email rendering and store templates as files under `mysite/emails/email_templates/`. Each template uses a single Django template file that exposes named blocks for subject, plaintext body, and HTML body (with fallback support for alternative layouts). The email service loads, caches, and renders these templates, producing plain text and optional HTML for downstream transports.

### Key Elements
1. **Template Source Layout**
   - Directory: `mysite/emails/email_templates/`, where each email lives under a single logical base name (e.g., `verification`, `password_reset`).
   - Django template syntax allows filters, includes, and translation tags.
   - See “Subject/Body Authoring Options” for how the subject/text/HTML pieces are stored.

2. **Loader & Cache**
   - Introduce `EmailTemplateLoader` that scans the directory at startup (AppConfig `ready()`), compiles Django templates, and registers them with `email_dispatch_service`.
   - Cache compiled templates in memory; reload automatically in development when `DEBUG` is true by watching file modification times.

3. **Rendering Contract**
   - Extend `EmailTemplate.render()` to return a `RenderedEmail` dataclass containing `subject`, `text_body`, and optional `html_body`.
   - Loader renders each defined block. If `text_body` is missing, derive it by stripping HTML; if `html_body` is missing, send only text.
   - Service returns the enriched structure; transports decide which representation to send.

4. **Transport Enhancements**
   - Update Mailjet payload builder to include HTML and text parts when available.
   - Configure Django email backend to send multipart/alternative messages when both parts exist.

5. **Developer Workflow**
   - Provide `manage.py render_email <template> [--context path.json]` for previews.
   - Document conventions in `docs/guides/email-templates.md`, including context variables and recommended partials.

### Subject/Body Authoring Options
- **Recommended: Single Django template with named blocks**
  - Store one template file per email (e.g., `verification.email.html`) that defines `{% block subject %}`, `{% block text_body %}`, and `{% block html_body %}`.
  - Keeps all content together, supports inheritance/partials, and allows HTML + plaintext in one artifact.
  - Loader renders each block separately; missing blocks fall back to derived values (e.g., `text_body` falls back to stripped `html_body`).
- **Alternative: Parallel files per artifact** (`*_subject.txt`, `*_body.txt`, `*_body.html`)
  - Simple to parse but fragments authoring across files and makes cohesive editing harder.
- **Alternative: Front-matter metadata** (YAML/JSON at top of template)
  - Allows subject and headers to live in metadata while body stays in template, but requires custom parser and increases coupling to file structure.

We recommend the single-template-with-blocks approach for its ergonomics and consistency with Django templating, while keeping support for legacy Python-registered templates during migration.

### Incremental Migration Plan
1. Implement loader and service wiring while keeping legacy Python-registered templates operational.
2. Convert the verification email to file-based templates and add regression tests comparing legacy outputs.
3. Migrate the remaining templates, removing inline definitions after tests pass.
4. Enforce via lint/CI that new templates must be file-based.

## Consequences

### Benefits
- Enables HTML-rich, designer-friendly emails without code deployments for copy edits.
- Centralizes template discovery, improving test coverage and tooling.
- Simplifies localization by leveraging Django's translation mechanisms.
- Keeps the existing task/service contract intact while increasing flexibility.

### Risks / Trade-offs
- Initial implementation and migration effort.
- Template syntax errors become runtime rendering issues; mitigated with unit tests and the preview command.
- File I/O during startup adds a small overhead, offset by caching.

## Alternatives Considered
- **Status quo (inline Python templates):** No migration cost but retains current limitations.
- **Jinja2 or MJML engines:** Offer specialized features but introduce new dependencies and configuration.
- **Database-managed templates:** Supports live editing but requires substantial tooling for versioning and audit.

## Follow-Up Actions
1. Build `EmailTemplateLoader` and integrate it with `email_dispatch_service` while supporting legacy registration for transition.
2. Convert the verification template files and add rendering tests.
3. Migrate all remaining templates, delete inline definitions, and update documentation.
4. Add the preview CLI and CI guardrails for file-based templates.
