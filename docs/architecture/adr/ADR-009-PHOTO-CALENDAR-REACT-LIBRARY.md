# ADR-009: Tinybeans-Inspired Photo Calendar React Library

## Status
Proposed - Date: 2025-10-03

## Context
We want a reusable React library that renders a month-view calendar where each day can display one or more photo thumbnails, similar to Tinybeans. The component should be embeddable in our web app(s), be accessible, performant with large photo libraries, and flexible enough to support custom styling and data-fetching strategies.

### Goals
- Month grid that respects locale (first day of week, weekday labels) and time zones.
- Each day cell can display thumbnails (1-N), overflow indicator (+3), and quick actions.
- Smooth navigation across months (swipe on mobile, buttons/keyboard on desktop).
- Fast rendering and scrolling with lazy-loaded images, LQIP/blurhash placeholders, and virtualization for multi-month views.
- Headless/unstyled by default, with render-prop or slot APIs for full UI control.
- Works with any data source (REST/GraphQL/TanStack Query).
- Strong accessibility (keyboard navigation, ARIA semantics, readable counts/labels).

### Non-Goals (initial)
- Full event scheduling (drag-resize timeslots, recurring events, calendars beyond month grid).
- Opinionated global state or network client.
- Image upload/picking/ingestion flows (dropzones, camera access, EXIF writing). The library consumes already-hosted thumbnails/URLs only.
- Published as a separate React library in its own folder/repository structure (not embedded in the app source tree). Uses a shared browserslist for tooling targets.


## Requirements
1. Rendering & Navigation
   - Monthly grid with weekday headers; supports min/max date bounds.
   - Navigate previous/next month, jump-to-month/year, swipe gestures (optional) on touch.
   - Programmatic control (controlled and uncontrolled modes).

2. Day Cell & Thumbnails
   - Display first N thumbnails per day (configurable), with a "+X" overflow badge.
   - Support multiple categories/streams (e.g., per tag or album) with subtle indicators (color/ring/badge).
   - Day detail view (popover/modal) to browse all items for the day.
   - Optional drag & drop between days (re-dating photos) with callbacks.

3. Media Handling
   - Lazy load images with IntersectionObserver.
   - Responsive images (srcset/sizes) and capped decoding to avoid jank.
   - LQIP/blurhash placeholders until images load.
   - EXIF date parsing (optional hook) to suggest placement when uploading.

4. Data & Integration
   - Headless data contract: consumer supplies items and handlers.
   - Range-based data fetching hooks (e.g., onRangeChange from first-to-last visible date).
   - i18n and timezone support; deterministic day boundaries.

5. Accessibility
   - Roving tabindex for day cells; arrow-key navigation; enter/space to open day.
   - ARIA roles/labels (grid, gridcell, row, rowheader); readable overflow counts.
   - High-contrast and reduced-motion support.

6. Performance
   - O(visible days) render; avoid list re-creation on navigation.
   - Preload adjacent months’ metadata; prefetch images on hover/focus.
   - Optional virtualization for infinite month scroller.

7. Theming & Extensibility
   - Unstyled primitives with className/style passthroughs.
   - Slot/render-prop APIs for DayCell, Thumbnail, OverflowBadge, EmptyState.
   - Works with Tailwind, CSS Modules, or CSS-in-JS; no styling dependencies.


### Day Cell Thumbnail Layout Options
- Default (Tinybeans-style): show a single “hero” thumbnail for the day. If multiple photos exist, display a small “+X” overflow badge; activating the cell opens the day detail to browse all.
- Optional mini-collage: render up to N thumbnails (2–4) in a fixed pattern (e.g., 2-up, 3-up, or 2x2). Still show a +X badge if more exist.
- Optional stack: visually stack 2–3 thumbnails with slight offsets and a +X badge.

Hero selection strategies (configurable):
- Latest-by-timestamp (default)
- Favorited/pinned first
- First-of-day
- Custom selector callback

Accessibility:
- aria-label pattern: “Oct 12, 3 photos” (customizable)
- Keyboard: focusable gridcell; Enter/Space opens detail

## Options Considered
1. FullCalendar (React adapter)
   - Pros: battle-tested navigation, many features, plugins.
   - Cons: heavy for thumbnail-first use; event-centric model; license/SSR constraints; custom day content is possible but awkward for image grids.
   - Verdict: Not ideal for a photo-first month view library.

2. react-big-calendar
   - Pros: robust month/week views, good keyboard support.
   - Cons: event scheduling bias; CSS opinions; customizing day cells for stacked thumbnails is non-trivial.
   - Verdict: Similar drawbacks to FullCalendar for our use case.

3. react-calendar / dayzed + custom cells
   - Pros: lightweight, minimal date math; easier to control rendering.
   - Cons: still need to build image stacking, overflow, lazy loading, a11y specifics, and perf tooling.
   - Verdict: Viable, but we may still rebuild many behaviors.

4. Build a headless, composable library (date-fns + headless grid + hooks)
   - Pros: smallest API surface tailored to photos; SSR-friendly; library-agnostic styling and data; easy to tree-shake.
   - Cons: More initial work; we own a11y and perf details; more docs required.
   - Verdict: Best fit for our domain and long-term flexibility.

## Decision
Build a headless, composable React library named `@tinybeans/photo-calendar` that provides:
- A month grid primitive (no styles) with render-prop slots for day cells and headers.
- Utilities for date math (date-fns), locale configuration, and timezone-safe day boundaries.
- Hooks for range calculation, keyboard navigation, lazy image loading, and optional virtualization.
- Default day cell behavior: single hero thumbnail per day (Tinybeans parity) with a “+X” overflow indicator when multiple photos exist; day detail opens to view all.
- No default theme package. We will provide example implementations only to demonstrate styling approaches; the library ships unstyled primitives exclusively.

## Architecture Overview
Components (unstyled):
- Calendar: orchestrates month view; controlled via `month` and `onMonthChange` or uncontrolled with internal state.
- MonthGrid: renders weekday headers and day cells, emitting visible range.
- DayCell: render-prop for day content with states (today, selected, outsideMonth, hasItems).
- ThumbnailStack: utility to layout N thumbnails + overflow.
- DayDetail: headless container for modal/popover content (leave modal lib choice to consumer).

Hooks:
- useCalendarGrid({ month, firstDayOfWeek, timezone }) -> { weeks, days, visibleRange }
- useMonthNavigation({ initialMonth, min, max, onChange })
- useLazyImages({ rootMargin, decodeStrategy })
- useKeyboardNav({ onSelectDay, onOpenDay, gridRef })
- useVirtualMonths(optional) for infinite month scrollers.

Data shape suggestions (consumer-provided):
```
PhotoItem {
  id: string
  date: string | Date // normalized to midnight in timezone
  thumbnailUrl: string
  blurhash?: string
  childId?: string
  tags?: string[]
}
```
Library groups items by day; consumers pass `itemsByDate` or `items` and a `groupBy` function.

## Public API (draft)
- <Calendar
    month={Date}
    onMonthChange={(next: Date) => void}
    min?: Date
    max?: Date
    locale?: Locale
    timezone?: string
    onRangeChange?={(range: { start: Date; end: Date }) => void}
    renderDay={(ctx) => ReactNode}
    renderWeekdayHeader?={(weekday: Date) => ReactNode}
  />
  // Thumbnail layout options
  // Default: single hero thumbnail with +X indicator (Tinybeans parity)
  // Optional: mini-collage or stack via props

- Example usage:
```
<Calendar
  month={current}
  onMonthChange={setMonth}
  // Tinybeans-style single image per day
  maxThumbnailsPerDay={1}
  thumbnailLayout="hero"
  renderDay={({ date, items, overflow, isToday }) => (
    <DayCell date={date} isToday={isToday}>
      <img src={selectHero(items).thumbnailUrl} alt="" loading="lazy" />
      {overflow > 0 && <span className="overflow">+{overflow}</span>}
    </DayCell>
  )}
/>

// Optional collage
<Calendar maxThumbnailsPerDay={3} thumbnailLayout="grid" ... />
```


## Additional Ideas (Future Enhancements)

User experience and interactions
- Day detail navigation: keyboard left/right and touch swipe to previous/next day within the detail view. [P2]
- Quick-jump controls: Today button [P1], jump-to-month/year picker [P2], optional year grid [P3].
- Overflow indicator: configurable +X badge position and tooltip/label; click/tap opens day detail. [P1]
- Status overlays: weekend shading [P2], holiday/anniversary markers via a badges slot [P3].
- Streaks/heatmap: indicate activity streaks or density shading for days with more photos. [P3]
- Selection: controlled selectedDate/range props; onDayClick/onOpenDetail callbacks. [P1]
- Context menu: actions like share link, copy date, pin as hero (via callback). [P2]

Data, filtering, and grouping
- Filters: tags, albums, favorites; header shows active filters. [P2]
- Grouping: monthly summaries per tag/album; aggregate counts by group. [P3]
- Empty-day states: customizable placeholders (dot/icon/label) via a slot. [P1]
- Range-driven fetching: robust onRangeChange (start/end UTC), with debounced notifications. [P1]

Accessibility and localization
- ARIA live region announcements for month changes and filter changes. [P2]
- Localized formats and firstDayOfWeek per locale. [P1]
- Reduced-motion variants for image transitions; high-contrast-safe overlays. [P1]

Performance and media handling
- Avoid CLS: require or infer aspect ratio for thumbnails; helpers to maintain boxes. [P1]
- CDN helpers: build srcset/sizes; optional transform hook for URL params. [P2]
- Priority prefetch: prefetch current-week heroes; hover/focus preloads day detail images. [P2]
- Image error handling: broken-image fallback component and onImageError callback. [P1]

API and developer experience
- Headless slots: DayBadge, DayFooter, DayCorner, EmptyState, WeekHeader, MonthHeader. [P1]
- Imperative handle: ref methods openDay(date), focusDay(date), scrollToMonth(date). [P2]
- Strong TypeScript types; discriminated unions for layout modes. [P1]
- Event hooks: onDayFocus, onDayKeyDown, onMonthChange, onRangeChange, onOpenDetail. [P1]
- Optional state adapter to persist last viewed month. [P2]

Integrations
- TanStack Query example: wire onRangeChange to query keys and cache prefetch. [P2]

Printing and export
- Print-friendly CSS for the month grid. [P2]
- Optional “export month as image” helper via html-to-canvas (kept external and opt-in). [P3]

Testing and quality
- Storybook stories covering empty/overflow/a11y states. [P1]
- A11y tests for keyboard nav and screen reader labels. [P1]
- Visual regression test for the month grid with varied content. [P2]

Safety and privacy
- Default alt text uses count summaries (e.g., "Oct 12, 3 photos"); never embeds PII by default.
- Library does not perform network calls; images are loaded only from provided URLs.


### MVP vs. Later Phases

MVP (Phase 1)
- Month grid with weekday headers and locale/firstDayOfWeek
- Controlled/uncontrolled month navigation with min/max bounds
- Day cell with single hero thumbnail and +X overflow indicator
- Day detail view (headless container) and open/close callbacks
- Range reporting via onRangeChange(start/end UTC)
- Keyboard navigation (roving tabindex, arrows) and basic ARIA roles
- Lazy-loaded images with srcset/sizes helpers and aspect ratio to avoid CLS
- Render hooks/slots (renderDay, WeekHeader, MonthHeader, EmptyState)
- Browserslist-defined targets; no bundled polyfills

Later Phases (Phase 2+)
- Optional collage/stacked thumbnails per day (maxThumbnailsPerDay, thumbnailLayout)
- Streaks/heatmap overlays and status/badges slots
- Quick-jump picker and year grid
- Drag & drop between days with callbacks
- Filters and grouping summaries (tags/albums/favorites)
- Imperative methods (openDay, focusDay, scrollToMonth)
- Priority prefetching and image error handling hooks
- Print-friendly CSS and optional export-as-image utility
- TanStack Query integration example
- Visual regression tests and enhanced a11y test coverage

  maxThumbnailsPerDay?: number // e.g., 1 (default), 2, 3, 4
  thumbnailLayout?: 'hero' | 'stack' | 'grid' // default 'hero'
  selectHero?: (items: PhotoItem[]) => PhotoItem // override hero selection


- Day render ctx: `{ date, isToday, isCurrentMonth, items: PhotoItem[], overflow: number, props }`

- Helpers: `getMonthVisibleRange`, `groupItemsByDay(items, { timezone })`, `isSameDay`.
- Browser support is defined via browserslist; no runtime polyfills are bundled by default.


- Styles: zero by default; all components accept `className`/`style`.

## Accessibility
- ARIA grid semantics; row/rowheader/gridcell roles.
- Roving tabindex with arrow key navigation across days.
- Screen-reader labels: "October 12, 3 photos"; configurable via formatter.
- Focus-visible outlines and reduced motion for image transitions.

## Performance Considerations
- Render only visible month; memoize day cells; stable keys by date.
- IntersectionObserver-based image loading; `loading="lazy"` as baseline; optional `decode()`.
- Preload adjacent months’ metadata; small prefetch window for images on hover/focus.
- Optional virtualization for multi-month infinite scroll using `@tanstack/react-virtual`.

## Alternatives & Trade-offs
- Using FullCalendar/react-big-calendar speeds up navigation plumbing but complicates image-first rendering and adds weight.
- Building headless gives full control and the best UX, but increases our maintenance cost.
- A hybrid approach (wrapping react-calendar/dayzed) reduces date math, but we still own most features.

## Implementation Plan (Phased)
1. MVP (Weeks 1-2)
   - Calendar + MonthGrid primitives; date-fns integration; locale/timezone options.
   - Basic day cell with thumbnail stack and overflow badge; lazy loading; keyboard nav.
   - Range reporting and controlled/uncontrolled modes.

2. UX Enhancements (Weeks 3-4)
   - Day detail view (headless) with example modal; swipe/arrow navigation within day.
   - Drag & drop between days (feature-flagged) via HTML5 DnD; callbacks only.
   - Blurhash/LQIP support; example usage only (no theme package).

3. Optimization & Docs (Weeks 5-6)
   - Optional virtualized multi-month scroller.
   - Benchmarks, a11y audit, Storybook docs, integration examples (TanStack Query, Next.js SSR).

## Open Questions
- What’s the minimum browser support matrix? We will define targets via a shared browserslist configuration used by bundlers, Babel, and PostCSS.
- Should we publish a separate examples repo or colocate examples in a /examples folder of the library?

## Consequences
- Pros: Tailored UX for photos; flexible and future-proof; easy to embed and theme.
- Cons: We own maintenance and a11y/perf details; initial build time compared to adopting a calendar lib.

## Security & Privacy
- Avoid embedding PII in alt text by default; allow consumer-defined ARIA labels.
- Respect CSP; no inline styles/scripts required.
- Ensure no third-party network calls from the library itself.

## Decision Record
We will implement `@tinybeans/photo-calendar` as a headless React library with primitives and hooks, using date-fns for date utilities, optional TanStack Virtual for virtualization, and example-only styling. We will not adopt FullCalendar or react-big-calendar for this use case.
