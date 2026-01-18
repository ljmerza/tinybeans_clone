# ADR-0007: Circle Membership Invitation Auto-Prune

Date: 2025-10-22T18:36:57.649Z
Status: Accepted
Decision: Adopt "Auto-Prune Accepted Invitations" backend strategy.

## Context
Circle dashboard currently shows invitations; accepted invitations linger causing duplicates / ghost entries after membership creation or removal. Original exploration considered a client-side merge plus several backend options.

## Problem
Users can appear twice (member + accepted invitation) or remain visible after removal. This degrades UX clarity and complicates removal logic.

## Options Considered (Summary)
- Client Merge Layer (pure FE suppression)
- Backend Combined Endpoint (/participants)
- Auto-Prune Accepted Invitations (selected)
- Realtime Sync (events/WebSocket)
- Materialized View + Stream

## Decision
Implement backend auto-prune: upon successful acceptance convert invitation → membership and archive (exclude from default /invitations/). On member removal archive any associated accepted invitation rows. Support `?include=archived` for audit retrieval.

## Rationale
- Eliminates duplicate rendering without client suppression complexity.
- Minimal backend lift vs new aggregate endpoint.
- Preserves audit trail via archived flag + optional query param.
- Reduces FE branching logic & transitional shimmer states.

## Consequences
### Positive
- Single authoritative source for active + pending items.
- Simpler FE: invitations list == pending only.
- Faster perceived consistency (no race between endpoints).

### Negative / Trade-offs
- Need migration script to mark historical accepted invitations as archived.
- Slight added backend logic (state transition + archival).
- Must define retention & indexing strategy for archived rows.

## Implementation Outline
1. Add `archived_at` (timestamp) + `archived_reason` columns to invitations table.
2. Acceptance flow: wrap in transaction → create membership → set `archived_at` on invitation.
3. Removal flow: find any invitations with `status='accepted' AND invited_user_id=<user>` → ensure `archived_at` set.
4. Default endpoint `/circles/{id}/invitations/` filters `WHERE archived_at IS NULL`; allow `?include=archived=true`.
5. Add partial index for active invitations to keep query fast.
6. Backfill: one-off migration archiving all invitations with status='accepted' that have a membership.
7. Update FE: remove merge logic; rely on members + (pending only) invitations.
8. Tests: acceptance creates membership + archives invitation; removal archives existing accepted invitation; audit param returns archived set.

## Data Model Changes
```sql
ALTER TABLE circle_invitations
  ADD COLUMN archived_at timestamptz NULL,
  ADD COLUMN archived_reason text NULL;
CREATE INDEX CONCURRENTLY idx_circle_invitations_active
  ON circle_invitations(circle_id)
  WHERE archived_at IS NULL;
```

## API Contract Changes
- `/circles/{id}/invitations/` (unchanged path) now returns only pending (and optionally declined/cancelled/expired depending on product rules) but excludes accepted unless `include=archived`.
- Document new query param in API docs.

## Monitoring & Metrics
- Track count of archived invitations per day.
- Alert if accepted invitations without membership remain unarchived >5m.

## Alternatives Rejected
- Client Merge: still leaves duplication risk for other clients; more FE complexity.
- Combined Endpoint: broader change without immediate need.
- Realtime Sync: infra overhead not justified yet.
- Materialized View: premature complexity.

## Rollback Plan
If archival causes unforeseen issues, revert filter (serve full set) while FE reinstates suppression logic. Keep columns; disable archival triggers.

## Follow-up Tasks
- [ ] Schema migration PR
- [ ] Service layer updates for acceptance/removal flows
- [ ] Backfill script
- [ ] API docs update
- [ ] Frontend adjustment (remove combined list concept)
- [ ] Monitoring dashboards

## Open Questions
- Retention policy for archived invitations? (Indefinite vs TTL purge)
- Should declined/cancelled also be archived for consistency?
- Do we expose counts of archived invitations for analytics?

