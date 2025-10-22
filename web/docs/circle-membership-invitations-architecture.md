# Circle Membership & Invitation Consolidation

## Problem Overview
Currently the Circle dashboard displays "Circle members & invitations" using only the invitations dataset. A person can exist simultaneously in two backend resources:

- `GET /circles/{id}/members/` – authoritative list of active circle members
- `GET /circles/{id}/invitations/` – pending (and historically accepted / declined / expired) invitations

When a user accepts an invitation they become a member, but the accepted invitation record may still be returned (status = accepted) and we presently surface invitations directly, so the same logical person can appear twice (or linger after removal):

1. Remove member via members endpoint → entry disappears from members list
2. Accepted invitation object (or orphan invitation pointing to removed user) remains → still rendered in UI

This causes confusing UX (ghost / duplicate entries) and additional edge‑case handling in removal flows.

## Goals
- A user should appear at most once in the combined UI list.
- Accepted invitations should not render once a membership exists.
- Removing a member should not leave an accepted invitation visible.
- Keep pending invitation management actions (resend, cancel) intact.
- Minimize additional network requests and cache invalidation complexity.

## Constraints & Existing Patterns
- Frontend already fetches members (`useCircleMembers`) and invitations (`useCircleInvitationsQuery`).
- Invitation list controller performs member resolution heuristics (see `findMemberId`).
- We use React Query; want to preserve normalized cache keys (`circleKeys.members`, `circleKeys.invitations`).
- Backend APIs may continue returning accepted invitations for audit/compliance.

## Proposed Primary Approach (Client Merge Layer)
Create a derived, memoized combined data structure that merges members and invitations into a single presentational array.

### Rules
1. Pending invitations (status=pending) always shown.
2. Declined / cancelled / expired invitations optionally hidden behind a filter (default: hide) unless we need audit visibility.
3. Accepted invitations are suppressed when a member with matching user id exists.
4. If an accepted invitation references a user id not present in members (race condition) we show as a transitional state with a shimmer / syncing badge for a short TTL (e.g. 5s) while refetching members.
5. Removal of a member triggers invalidation of both members & invitations queries; accepted invitation will then be filtered out (or backend should soft‑delete / mark historical so frontend hides).

### Data Shape
```ts
interface CombinedCircleEntry {
  kind: 'member' | 'invitation';
  id: string;            // stable key (member: membership_id, invitation: invitation.id)
  status?: CircleInvitationStatus; // invitations only
  role: string;          // target or actual role
  email?: string;        // invitations
  user?: CircleUserSummary; // members
  created_at: string;
  meta?: { transitional?: boolean };
}
```

### Implementation Sketch
```ts
const members = membersQuery.data?.members ?? [];
const invitations = invitationsQuery.data ?? [];

const memberUserIds = new Set(members.map(m => m.user.id.toString()));

const combined: CombinedCircleEntry[] = [
  ...members.map(m => ({
     kind: 'member',
     id: `member-${m.membership_id}`,
     role: m.role,
     user: m.user,
     created_at: m.created_at,
  })),
  ...invitations.filter(inv => {
     if (inv.status === 'pending') return true;
     if (['declined','cancelled','expired'].includes(inv.status)) return false; // base policy
     if (inv.status === 'accepted') {
       const uid = inv.invited_user?.id ?? inv.invited_user_id;
       if (uid && memberUserIds.has(uid.toString())) return false; // suppress
       return true; // transitional acceptance – member record not yet visible
     }
     return true;
  }).map(inv => ({
     kind: 'invitation',
     id: `invite-${inv.id}`,
     status: inv.status,
     role: inv.role,
     email: inv.email,
     created_at: inv.created_at,
     meta: inv.status === 'accepted' ? { transitional: true } : undefined,
  })),
];
```

### UI Adjustments
- Replace direct `invitations.map(...)` render with `combined.map(...)`.
- Present badges:
  - Pending → existing actions
  - Transitional accepted (no member yet) → badge: "Joining…"; auto refetch members after short interval.
- Hide actions (resend/cancel) for accepted transitional state once member appears.

### Query Invalidation
- On successful acceptance finalize flow (existing invitation accept page) → invalidate `members` first, then `invitations`.
- On member removal → invalidate both; combined selector ensures accepted invitation suppressed.

### Advantages
- No backend changes required.
- Minimal risk: purely additive selector & small UI change.
- Works with current caching; easy to test.
- Clear suppression logic encapsulated centrally.

### Potential Drawbacks
- Duplicates suppression logic lives only on client; other consumers must replicate approach.
- Historical invitation states lost in dashboard unless separate “History” view.

## Alternative Architectures

### A. Backend Normalization Layer
Modify backend to return a single `/circles/{id}/participants/` endpoint combining current members + pending invitations (excluding accepted). Accepted invitation rows converted into member objects server‑side once membership transaction commits.

Pros:
- Single source of truth; all clients consistent.
- Simplifies frontend (one query).
Cons:
- Requires backend change & migration of existing clients.
- Potential coupling; harder to evolve invitation lifecycle independently.

### B. Soft Deletion / Auto-Prune Accepted Invitations
Upon acceptance, backend marks invitation as archived (not returned by `/invitations/` unless `?include=archived`). Removal of member also archives related accepted invitation rows.

Pros:
- Keeps existing endpoints; small change.
- Frontend logic stays simple (accepted never seen).
Cons:
- Loses immediate ability to audit acceptance timestamp without extra flag/endpoint.
- Edge cases if archival fails → ghost states persist.

### C. Server Event / WebSocket Sync
Emit real‑time event on invitation acceptance & member removal; client updates caches in place removing accepted invitation entries.

Pros:
- Fast UI consistency; fewer refetches.
- Good for multi‑user live dashboards.
Cons:
- Infra overhead; need real‑time channel.
- Still need fallback suppression on initial load.

### D. Materialized View + Incremental Stream
Maintain materialized participant view (member_or_pending_invitation) consumed via SSE/WebSocket; invitations table purely historical.

Pros:
- Clear separation of current vs history.
- Scales for analytics & auditing.
Cons:
- Complexity disproportionate to current needs.

## Decision Matrix
| Option | FE Complexity | BE Effort | Consistency | Audit Support | Time-to-Ship |
|--------|---------------|----------|-------------|---------------|--------------|
| Client Merge (Primary) | Low | None | Good (eventual) | Raw data still accessible | Fast |
| Backend Combined Endpoint | Low | Medium | High | High | Medium |
| Auto-Prune Accepted | Low | Low-Med | High (if reliable) | Medium (need include flag) | Medium |
| Realtime Sync | Medium | Medium-High | High (fast) | High | Medium-High |
| Materialized View | Low (client) | High | High | High | Slow |

## Recommended Path
Adopt the Primary Client Merge Layer now for rapid elimination of duplicate/ghost entries. Revisit Backend Normalization or Auto-Prune once product requirements for invitation history & auditing mature.

## Follow-Up Tasks
1. Implement combined selector hook `useCircleParticipants(circleId)`.
2. Replace `CircleInvitationList` rendering data source with combined list (rename component to `CircleParticipantsList`).
3. Add suppression tests (cases: pending only, accepted+member, accepted without member until refetch, declined hidden, removal invalidation).
4. Add optional toggle to show historical invitations (behind small disclosure / menu) if needed.
5. Capture metrics: time from acceptance → member visibility; count of transitional states > N seconds.
6. Create ticket to evaluate backend pruning after metrics collected.

## Open Questions
- Do we need to expose historical accepted/declined invitations in-dashboard? If yes, UI pattern? (separate collapsible section?)
- SLA tolerance for transitional state before forcing a hard refresh?
- Should removal action soft-cancel related pending invitations simultaneously?

---
Document created: 2025-10-22
