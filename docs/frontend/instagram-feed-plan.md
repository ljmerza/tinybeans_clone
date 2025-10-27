# Instagram-Style Feed Implementation Plan

## 1. Goal & Non-Goals
- Deliver a vertically scrolling, media-first feed that mirrors Instagram’s interaction model (photos/videos, double-tap likes, inline comments).
- Keep perceived scrolling smooth by virtualizing oversized media entries and deferring heavy work off the main thread.
- Preserve privacy defaults: posts remain scoped to the author’s circle memberships and only fetch for authorized viewers.
- Out of scope for first pass: story carousel, direct messaging from the feed, live streaming, or AI curation.

## 2. Success Criteria
- Time-to-first-render under 1.5 s on modern mobile hardware with warm cache; <2.5 s on cold start.
- 60 fps scroll at the 95th percentile for feeds containing at least 500 items.
- P95 media lazy-load <350 ms once an item enters the viewport.
- Optimistic like/comment mutations resolve within 300 ms or show resilient retry UI.
- Automated regression suite covers feed queries, pagination edge cases, and optimistic interaction flows.

## 3. UX Scope
- Endless feed with pull-to-refresh, double-tap-to-like, long-press affordances, and inline “view all comments”.
- Sticky composer bar for adding comments; modal sheet for viewing all reactions.
- Inline indicators for processing uploads (ties into existing keeps async pipeline).
- Error/empty states for “no posts yet”, offline mode, and rate limiting.
- Respect system accessibility: large text, prefers-reduced-motion, VoiceOver labels on interactive icons.

## 4. Frontend Architecture
**Stack Alignment**  
- Reuse TanStack Router + Query already powering SPA; standardize on TanStack Virtual (`@tanstack/react-virtual`) for list virtualization.
- Extract shared feed logic into `packages/feed-virtualizer/` npm workspace library (private initially). Host feed route wrapper in app code, but keep virtualization hooks/components inside the package for reuse across surfaces.

**Data Fetching & Caching**  
- Feed hook `useFeedQuery({ circleId, cursor, filters })` wraps paginated GET `/api/feed/`.
- Likes/comments mutate via `useLikeMutation`, `useUnlikeMutation`, `useCommentMutation`, all updating Query caches optimistically. Use `meta.toast` for failure feedback to reuse existing toast pipeline.
- Prefetch next page during idle periods using `queryClient.prefetchInfiniteQuery`.

**Virtualization Strategy**  
- Use TanStack Virtual’s window ref to recycle DOM nodes, but retain media elements to avoid re-buffering video. Implement `overscan={2}` and dynamic measurement callback for posts with expanded comments. Export as `useInstagramFeedVirtualizer` hook from new npm package.
- Handle masonry vs single-column: start single-column to reduce complexity; revisit multi-column after MVP.
- Intersection Observer tracks when posts become visible to kick off media requests or analytics events.

**Media Handling**  
- Integrate keeps thumbnail & streaming URLs. Poster images load first; videos opt into `preload="metadata"` to limit bandwidth.  
- Use `<picture>` with AVIF/WebP fallbacks for photos; HLS/DASH for longer videos via existing CDN transcodes.

**Interactions & State**  
- Gesture support: double-tap detection via pointer events; haptic feedback on mobile if available.  
- Comments composer uses controlled input with autosize; submit on tap or `Cmd+Enter`.
- Offline queue: persist pending likes/comments locally (IndexedDB) and replay when connectivity returns.

## 5. Backend/API Requirements
- New DRF view `FeedViewSet` w/ `list` on `/api/feed/` supporting cursor pagination, filter by circle IDs, media types, or hashtags (future).  
- Query assembles timeline from `keeps` posts joined with author info, like counts, current user like state, top N comments, and comment counts.
- Likes: ensure existing `POST /api/keeps/{id}/likes/` supports idempotency and returns aggregate counts for optimistic updates.
- Comments: extend comment serializer to surface `created_at`, author avatar, redact deleted comments.
- Rate limiting: re-use Redis-backed limiter for like/comment endpoints to prevent spam.
- Audit logging: extend 2FA/OAuth audit log pipeline to cover feed interactions for compliance.

## 6. Data Model Considerations
- Ensure `Keep` model exposes denormalized counters (likes_count, comments_count) updated by signals or Celery tasks for cheap reads.
- Add `FeedEntry` materialized view (managed by Celery beat) if query plans degrade at scale; start with direct DB query + indexes on `(circle_id, created_at DESC)`.
- Consider storing per-user “last seen” timestamp for unread indicators.

## 7. Pagination & Ordering
- Cursor-based pagination using tuple `(created_at, id)` to maintain stable ordering despite concurrent posts.
- Support `?before=` and `?after=` cursors for both downward infinite scroll and pull-to-refresh top-up.
- Pre-compute pinned posts per circle and inject ahead of normal flow without breaking cursors.

## 8. Real-Time Updates (Phase 2+)
- Option A: Server-Sent Events endpoint pushing new feed items & interaction deltas.  
- Option B: WebSocket channel piggybacking on existing Redis pub/sub to broadcast likes/comments.  
- For MVP, rely on periodic refetch on window focus and background sync (navigator service worker).

## 9. Performance & Observability
- Measure with Web Vitals + custom `feed_scroll_jank` metric emitted via existing analytics pipeline.
- Add logging for slow feed queries (>200 ms) and cache effectiveness counters.
- Use CDN caching for media URLs with signed URL expiry; prefer HTTP/3 where possible.

## 10. Competitive & Library Survey
- **TanStack Virtual** (selected): actively maintained, first-class with TanStack Query, SSR-friendly; forms the core of our reusable library.  
- **React Virtuoso**: strong feature set (sticky headers, grouping) but larger bundle; could influence future features.  
- **React Virtualized / React Window**: older options with lighter bundles; useful benchmarks for performance comparisons.  
- **Framer Motion + Scroll-based animations**: optional for subtle parallax but ensure reduced-motion adherence.  
- Instagram-style UI kits (e.g., `react-insta-stories`) exist but lack enterprise accessibility/privacy controls—still helpful references.  
- Evaluate OSS references: `expo/react-native-virtualized-view` (mobile inspiration), `Next.js + Supabase Instagram Clone` repos for layout patterns.

## 11. Risks & Mitigations
- **Large media payloads cause scroll hitches** → aggressive lazy loading, background decoding, pause off-screen videos.  
- **Optimistic updates drift from server state** → reconcile responses, show toasts when mutations fail, throttle rapid toggles.  
- **Access control leaks** → enforce circle membership checks server-side; add integration tests.  
- **Virtualization & dynamic heights** → measure posts after image load; fall back to estimated heights and reflow using `virtualizer.measureElement`.

## 12. Testing Strategy
- Backend: pytest covering feed pagination, access controls, like/comment endpoints, counters. Use seeded fixtures in `mysite/test_settings`.  
- Frontend: Vitest + React Testing Library for hooks (query caching, optimistic updates) and component interaction snapshots. Add Playwright smoke test for scroll + interaction + offline queue.  
- Performance budget tests via Lighthouse CI in CI/CD (mobile emulation).  
- Observability: synthetic check hitting `/api/feed/` to verify 200s & response times.

## 13. Milestones & Deliverables
1. **Design & API Alignment (Week 0-1)** — Wireframes, endpoint schema review, confirm TanStack Virtual abstraction boundaries.  
2. **Backend Foundations (Week 1-2)** — Implement feed endpoint, counters, access control tests.  
3. **Library Bootstrap (Week 2)** — Scaffold `packages/feed-virtualizer`, expose virtualization hooks/components, document API.  
4. **Frontend MVP (Week 2-4)** — Integrate library into feed route, media rendering, likes/comments optimistic flows, loading/error states.  
5. **Performance Hardening (Week 4-5)** — Profiling, image optimization, offline queue, a11y polishing, publish library beta to private npm registry.  
6. **Real-Time & Analytics (Week 5+)** — Optional SSE/WebSocket integration, metric dashboards, iterative UX enhancements.

## 14. Distribution Strategy
- Treat `packages/feed-virtualizer` as an internal npm workspace package with semver releases; expose hooks (`useInstagramFeedVirtualizer`), presentational container (`FeedVirtualizer`), and utility types.  
- Publish to GitHub Packages/private npm registry after beta readiness; provide README with usage within `web` app and potential external surfaces (admin dashboards, mobile wrapper).  
- Add Storybook stories illustrating feed virtualization states for regression testing.  
- Ensure package exports remain tree-shakeable and typed (TS declaration maps on build).

## 15. Open Questions
- Do we prioritize multi-circle aggregate feed or per-circle feeds at launch?  
- Should likes/comments sync with existing notification system immediately or follow-up?  
- How do we unify moderation flags (spam, inappropriate content) within feed interactions?  
- What retention policy should apply to activity analytics derived from the feed?
