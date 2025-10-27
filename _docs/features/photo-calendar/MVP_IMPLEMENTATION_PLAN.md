# Photo Calendar React Library - MVP Implementation Plan

Status: Approved (based on ADR-009)
Date: 2025-10-03

## Scope (MVP)
Deliver a headless, unstyled React calendar library with a month view that displays a single hero thumbnail per day with a +X overflow indicator, day detail view (headless), and essential accessibility/performance features.

## Primary Photo Display Modes

The app will have **two main photo browsing modes**:

### 1. Calendar View (This MVP)

**Description**: Monthly calendar grid with one thumbnail per day + overflow indicator

**Behavior**:
- **Desktop**: Single month view with prev/next month navigation buttons
- **Mobile**: Infinite scroll through months (virtualized)

**Use case**: Date-based browsing, finding photos from specific dates

**Features**:
- Natural chronological organization
- Easy to find photos from specific dates
- Shows posting frequency/patterns
- Hero thumbnail per day with +X overflow indicator
- Click day to see all photos from that date

**Implementation**: Current MVP scope - React library in separate folder

### 2. Timeline/Feed View (Future)

**Description**: Instagram-style vertical feed showing photos in reverse chronological order (newest first)

**Behavior**:
- Infinite scroll (both desktop and mobile)
- Full-width or grid layout of photos
- Show captions, dates, reactions, comments inline

**Use case**: Social media-style browsing, catching up on recent updates

**Features**:
- Familiar UX pattern (Instagram/Facebook-like)
- Good for viewing recent photos
- Can show full-size images
- Easy to add captions, comments, reactions
- Grouped by date (e.g., "Today", "Yesterday", "Last Week")

**Implementation**: Separate component, infinite scroll with virtualization (@tanstack/react-virtual)

## View Comparison

| Feature | Calendar View | Timeline View |
|---------|---------------|---------------|
| **Primary use** | Date-based browsing | Recent updates |
| **Navigation** | Month-by-month | Continuous scroll |
| **Photo size** | Thumbnails | Full or large |
| **Photos per view** | ~30 days worth | Unlimited (scrollable) |
| **Date context** | Explicit (calendar grid) | Grouped headers |
| **Best for** | Finding specific dates | Passive browsing |

## Additional Features (Post-MVP)

These features will enhance both views but are not part of the initial calendar MVP:

- **Search/Filter**: Find photos by date range, tags, or content
- **Memories/Flashbacks**: "On This Day" style feature
- **Slideshow**: Full-screen presentation mode
- **Albums/Collections**: Curated groupings of photos
- **Day Detail View**: Click a day to see all photos in modal/drawer

## Package
- Name: `@photo-calendar/react` (working name)
- Distribution: ESM + CJS builds, type definitions
- Tooling: TypeScript, Vite (build), Rollup (bundle) or tsup, Jest/Vitest for unit tests, Storybook for playground
- Browserslist: shared config; no bundled polyfills

## MVP Feature Checklist
1) Month grid & navigation
- Controlled/uncontrolled month state
- Locale and firstDayOfWeek support
- Min/max bounds

2) Day cell & thumbnails
- Single hero thumbnail per day (default)
- +X overflow indicator when multiple items exist
- Render-prop API for cell content
- Configurable hero selection (default: latest)

3) Day detail (headless)
- Open on click/enter/space
- Close via escape/click outside
- Expose events: onOpenDetail(date), onCloseDetail(date)

4) Accessibility
- ARIA grid semantics for month grid
- Roving tabindex and arrow-key navigation
- Screen-reader labels (e.g., "Oct 12, 3 photos")

5) Data integration
- onRangeChange({ start, end }) notifications
- Accept items or itemsByDate; helper to group by day
- Timezone-safe day boundaries

6) Performance
- Lazy-loaded images (loading="lazy" + IntersectionObserver)
- srcset/sizes helper; aspect-ratio boxes to avoid CLS
- Memoized day cells; stable keys

7) Developer experience
- TypeScript types for public API
- Storybook stories (empty, few, many, overflow, a11y)
- Unit tests for date math, grouping, a11y nav

## Public API (Draft)
- <Calendar
    month={Date}
    onMonthChange={(d: Date) => void}
    min?: Date
    max?: Date
    locale?: Locale
    firstDayOfWeek?: 0|1|2|3|4|5|6
    timezone?: string
    onRangeChange?={(r: { start: Date; end: Date }) => void}
    renderDay={(ctx: DayRenderCtx) => React.ReactNode}
    renderWeekdayHeader?={(weekday: Date) => React.ReactNode}
    onOpenDetail?={(date: Date) => void}
    onCloseDetail?={(date: Date) => void}
    // Thumbnail options (MVP default = single hero)
    maxThumbnailsPerDay?: number // default 1
    thumbnailLayout?: 'hero' | 'stack' | 'grid' // default 'hero'
    selectHero?: (items: PhotoItem[]) => PhotoItem
  />

- DayRenderCtx: { date, isToday, isCurrentMonth, items: PhotoItem[], overflow: number, props }
- Helpers: getMonthVisibleRange, groupItemsByDay, isSameDay

## Work Breakdown & Timeline
Phase 1: Foundations (Week 1)
- Repo/package scaffold (tsconfig, package.json, browserslist)
- Date utilities (date-fns), timezone boundary helpers
- Types: PhotoItem, DayRenderCtx, public interfaces

Phase 2: Grid & Navigation (Week 1-2)
- useCalendarGrid hook (weeks/days/visibleRange)
- Calendar + MonthHeader + WeekHeader slots
- Controlled/uncontrolled state, min/max bounds
- Keyboard navigation and ARIA roles

Phase 3: Day Cells & Thumbnails (Week 2)
- DayCell primitive with renderDay
- Hero selection + +X overflow indicator
- Image component with lazy-load and srcset helpers

Phase 4: Day Detail (Week 3)
- Headless DayDetail controller (open/close state; events)
- Sample integration story with a minimal modal (example only)

Phase 5: Perf & A11y polish (Week 3)
- Memoization, stable keys, intersection thresholds
- a11y labels and focus management

Phase 6: Docs, Stories, Tests (Week 4)
- Storybook scenarios and MDX docs
- Unit tests for date math, grouping, keyboard nav
- Example integration with TanStack Query (range-driven fetch)

## Acceptance Criteria
- Renders a month grid and supports keyboard navigation
- Shows single hero thumbnail per day with +X overflow
- Triggers onRangeChange correctly for visible dates
- Day detail opens/closes via mouse and keyboard
- A11y basics pass (roles, labels, focus order)
- No CLS from thumbnails in common scenarios

## Out of Scope (MVP)
- Drag & drop between days
- Streaks/heatmap overlays
- Year grid and holiday overlays
- Printing/export helpers
- Virtualization and infinite scrolling

## Risks & Mitigations
- Timezone boundary bugs → add unit tests, centralize day-start/day-end logic
- Image performance/jank → enforce aspect ratios and defer decode
- A11y gaps → keyboard and screen-reader testing in Storybook + CI

## Tracking
- Link to ADR: docs/architecture/adr/ADR-009-PHOTO-CALENDAR-REACT-LIBRARY.md
- This plan: docs/features/photo-calendar/MVP_IMPLEMENTATION_PLAN.md

## Implementation Questions & Decisions

### Build & Tooling (DECIDED)
- **Build tool**: ✅ Vite
- **Testing**: Vitest (to match Vite ecosystem)
- **Location**: ✅ Separate top-level folder initially, split to npm package later
- **Package name**: `@photo-calendar/react` (can be scoped to @tinybeans later)

### Responsive Behavior (DECIDED)
Based on Q&A session 2025-10-27:
- **Desktop**: ✅ Single month view with prev/next navigation (as in original plan)
- **Mobile**: ✅ Infinite scroll (virtualized) through months
- **Data fetching**: ✅ onMonthInView callback fires when month becomes visible in viewport
- **Breakpoint**: TBD (suggest 768px)
- **Implementation approach**: Single component with responsive behavior OR two separate components? TBD

### TypeScript Type Definitions (PENDING)

#### PhotoItem Interface
```typescript
interface PhotoItem {
  id: string;
  url: string;           // full-size image URL
  thumbnailUrl?: string; // optional optimized thumbnail
  date: Date | string;   // when photo was taken/posted
  alt?: string;          // accessibility description
  width?: number;        // original width for aspect ratio
  height?: number;       // original height for aspect ratio
  // Additional fields TBD:
  // - caption/description?
  // - author/uploader?
  // - metadata (location, camera, etc.)?
}
```

#### API Updates Needed
Current plan shows:
```typescript
onMonthChange={(d: Date) => void}
```

Should be:
```typescript
// For viewport-based triggering (mobile scroll)
onMonthInView?(params: { month: Date; isVisible: boolean }) => void

// OR batch callback for all visible months
onMonthsInView?(months: Date[]) => void

// Debounce/throttle duration TBD
```

### Virtualization Strategy (MOBILE) - PENDING

**Questions to resolve:**
- Which library? Options:
  - `@tanstack/react-virtual` (lightweight, modern)
  - `react-window` (proven, stable)
  - `react-virtuoso` (feature-rich)
- **Recommendation**: @tanstack/react-virtual (aligns with TanStack Query usage)

- **Overscan count**: How many months to render outside viewport? (suggest 1-2)
- **Initial scroll position**: Start at current month or allow custom?
- **Scroll restoration**: Remember position on navigation away/back?

### Image Performance - PENDING

**Aspect ratio strategy:**
- Option A: Fixed 1:1 square (simplest, consistent)
- Option B: Fixed 4:3 or 3:2 (more natural for photos)
- Option C: Dynamic based on image metadata (best quality, complex)
- **Recommendation**: TBD

**Thumbnail sizes for srcset:**
- Suggested: `150w, 300w, 600w` for responsive images
- Need to confirm with backend/CDN capabilities

**Loading priority:**
- Current month: Eager load (priority)
- Adjacent months: Low priority lazy load
- Out of view: Deferred lazy load
- **Confirm**: Does backend support priority hints?

### Data Integration - PENDING

**Initial load behavior:**
- Should onMonthInView fire immediately on mount for current month? (suggest YES)
- Preload adjacent months on desktop? (suggest YES for prev/next)

**Controlled vs Uncontrolled:**
- Desktop mode: Controlled (parent manages current month state)
- Mobile mode: Uncontrolled (component manages scroll position)
- OR: Support both modes? TBD

**Data format:**
- Accept both `items: PhotoItem[]` AND `itemsByDate: Map<string, PhotoItem[]>`?
- OR: Only accept items array and use internal grouping helper?
- **Recommendation**: Items array only, internal grouping (simpler API)

### Out of Scope Updates - MOBILE INFINITE SCROLL

Note: Original plan listed "Virtualization and infinite scrolling" as out of scope.
**Update**: Mobile infinite scroll is now IN SCOPE for MVP based on requirements.

### Testing Strategy - PENDING

- **Unit tests**: Date math, grouping utilities, keyboard navigation
- **Integration tests**: Month transitions, data fetching callbacks
- **Visual regression**: Storybook + Chromatic? Percy?
- **A11y testing**: jest-axe + manual screen reader testing
- **Performance**: Lighthouse CI for image loading benchmarks?

### Open Questions

1. **Component naming**: `<Calendar>` or `<PhotoCalendar>`? Generic vs specific?
2. **Day detail implementation**: Modal, drawer, inline expansion? (Currently "headless" - consumer decides)
3. **Empty state**: How to handle days with no photos? Render empty cell or show placeholder?
4. **Today indicator**: Visual treatment for current day? (Likely consumer's responsibility via renderDay)
5. **Timezone handling**: Use browser timezone by default or require explicit prop?
6. **Min/max bounds**: Should navigation disable or hide out-of-bounds months?
7. **Keyboard shortcuts**: Just arrow keys or also vim-style (hjkl)? PageUp/PageDown for months?
8. **RTL support**: Handle right-to-left languages? (Suggest YES, use CSS logical properties)
9. **Month transitions**: Instant or animated? (If animated, headless allows consumer to implement)
10. **Error handling**: What if images fail to load? Callback for errors?
