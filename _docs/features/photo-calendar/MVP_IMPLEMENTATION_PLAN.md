# Photo Calendar React Library - MVP Implementation Plan

Status: Approved (based on ADR-009)
Date: 2025-10-03

## Scope (MVP)
Deliver a headless, unstyled React calendar library with a month view that displays a single hero thumbnail per day with a +X overflow indicator, day detail view (headless), and essential accessibility/performance features.

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
