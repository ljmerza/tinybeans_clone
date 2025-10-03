# ADR-012: Unified Notification Strategy

## Status
**Proposed** - *Date: 2024-06-06*  
**Owner:** Web Platform Team

## Context

Users currently receive duplicate notifications because domain events emitted by the API are echoed by optimistic UI feedback coded in the frontend. Both sources ship partially translated text, so the same message can arrive twice in different formats, and it is unclear which side should own the message catalogue. This increases the cost of adding new notifications, introduces translation drift, and makes it difficult to reason about the user experience across platforms.

We need a consistent strategy that:
- Defines a single source of truth for domain notifications versus purely local UI feedback.
- Clarifies when to render toast messages versus inline messaging.
- Establishes how localization keys flow through the stack so we translate each string exactly once.

### Current Implementation Findings (June 2024)

- The shared auth HTTP client (`authApi`) invokes `showApiToast` for every HTTP success or failure that carries a `message`/`detail` payload, so the backend text is toasted even when the frontend routes the outcome to inline components.
- Google OAuth link/unlink flows return strings from the API *and* explicitly call `toast.success` in `useGoogleOAuth`, which results in two identical success toasts for the same action.
- Two-factor setup, disable, and method-management endpoints return human-readable messages while the React wizard already renders contextual success panels, creating a toast + inline combination for every step.
- The 2FA settings page uses banners fed by server responses (remove method, switch default, remove trusted device) while the auto toast fires with the same copy, so users receive duplicated confirmations.
- Frontend-only experiences (e.g. OAuth callback routing or client-side validation failures) rely solely on UI messages today; these should remain frontend-owned under the new contract.

## Decision

1. **Domain events originate from the backend.** All API responses that need to notify users will include a `notifications` array. Each item carries metadata rather than already-formatted strings:
   - `id`: stable identifier for de-duplication (UUID or semantic key supplied by the backend).
   - `level`: `info`, `success`, `warning`, or `error`.
   - `channel`: `toast`, `inline`, or `modal` (future friendly for other surfaces).
   - `i18n_key`: canonical translation key (e.g. `notifications.profile.photo_uploaded`).
   - `default_message`: English fallback for logs and development.
   - `context`: optional payload (field references, CTA actions, etc.).

   Frontend clients render backend notifications by looking up `i18n_key` in the shared translation catalogue. The `default_message` is used only if the key is missing.

2. **Frontend-originated notifications are limited to local UX concerns.** The UI may raise notifications only for client-side validations, offline-mode feedback, or speculative UX hints while waiting on the server. These must reuse the same translation keys (sourced from the shared catalogue) and must not duplicate a domain event that will arrive from the API.

3. **Presentation rules determine toast versus inline usage.**
   - Use `inline` for contextual feedback scoped to a specific form, field, or component. These messages anchor near the triggering UI and are cleared when the user resolves the issue.
   - Use `toast` for global, ephemeral updates that acknowledge a completed action or cross-surface event (e.g. background sync, push events). Toasts should auto-dismiss but remain accessible in an activity center when appropriate.
   - Reserve `modal` (or other channels) for disruptive, decision-required flows (e.g. destructive confirmations). Modal usage requires explicit product approval.

4. **Internationalization lives in a shared catalogue.** Translation keys for notifications reside in the existing i18n pipeline (e.g. `locales/{lang}.json`). Backend code references the same keys by name, enabling continuous localization without duplicating translation work. Adding a new notification requires updating the catalogue once; both backend and frontend tests should fail fast if the key is missing.

5. **Deduplication is enforced on the client.** The frontend maintains a notification store keyed by `id`. When a backend response includes an `id` already displayed (within a configurable TTL), the UI will ignore the duplicate. Frontend-generated notifications must use a distinct namespace (e.g. `ui.local.` prefix) to avoid collisions.

6. **Transport-agnostic contract.** Whether notifications arrive via REST, GraphQL, or WebSocket push, the payload structure remains identical. Backend services that broadcast events (emails, push notifications) can reuse the same metadata, keeping message semantics consistent across channels.

### API Example

```json
{
  "data": { "photoUrl": "https://..." },
  "notifications": [
    {
      "id": "profile-photo-uploaded",
      "level": "success",
      "channel": "toast",
      "i18n_key": "notifications.profile.photo_uploaded",
      "default_message": "Profile photo updated successfully"
    }
  ]
}
```

## Consequences

- Backend work: add the `notifications` contract to relevant endpoints and migrate existing hard-coded message strings to i18n keys.
- Frontend work: update notification store to consume the new payload, enforce de-duplication, and route toasts versus inline messaging consistently.
- Localization work: ensure the translation pipeline exports/imports any new keys, and add tests that fail when a referenced key is missing.
- Transitional period: while migrating old flows, toggle a feature flag to prefer backend notifications; once coverage is complete, remove redundant frontend messages.

## Alternatives Considered

- **Status quo with manual coordination.** Rejected because it relies on developers to remember which side owns each message, which has already led to drift and duplication.
- **Backend sends fully translated strings.** Rejected because it complicates localization, requires language negotiation on every request, and couples backend deployments to translation updates.

## Follow-up Actions

1. Define the notification payload schema in shared API documentation and update OpenAPI specs.
2. Inventory current frontend-only notifications; remove or migrate any that overlap with new backend events.
3. Add automated tests (unit/integration) ensuring translation keys referenced by backend exist in the catalogue.
4. Schedule a UX review to align toast styling and inline message components with the new channels.
5. Change the shared HTTP client so success/error toasts are opt-in, then suppress auto-toast for flows that already provide inline messaging (2FA status, trusted devices, etc.).
6. Refactor Google OAuth and 2FA UI hooks to consume the upcoming `notifications` payload instead of hard-coded strings, ensuring only one surface (inline or toast) renders each message.
