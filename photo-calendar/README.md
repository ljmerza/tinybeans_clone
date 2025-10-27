# @tinybeans/photo-calendar (work in progress)

This folder hosts the stand-alone React + Vite workspace for the photo calendar
library. The code will eventually move into its own repository; for now it lives
alongside the main product so the team can iterate while shaping the public API
and reference playground.

## Getting started

```bash
cd photo-calendar
npm install
npm run dev
```

The dev command launches a local playground powered by Vite so contributors can
experiment with the headless primitives. The `build` script bundles the library
in ESM and CJS formats and emits TypeScript declarations that match the contract
outlined in ADR-009.

## Project layout

- `src/index.ts` – public exports for the library package.
- `src/PhotoCalendar.tsx` – temporary placeholder component to validate build
  output. Replace with the headless primitives as they are implemented.
- `example/` – local development harness powered by Vite (`example/main.tsx` is the dev entry point).
- `vite.config.ts` – configures library builds and test environment defaults.

The current playground only renders the month grid view; future work will flesh
out the headless primitives, data hooks, and theming slots described in ADR-009.

The example app imports from the package name (`@tinybeans/photo-calendar`) so
changes are exercised through the same surface area that downstream apps will
use. Update `example/App.tsx` when you need to demo new props or behaviours.

Use the optional `firstDayOfWeek` prop (0 = Sunday, 1 = Monday, …) to align the
placeholder grid with your locale while the production-ready date math evolves.

Navigation arrows appear on pointer/desktop contexts. Pass `monthKey` +
`onMonthChange` to control the current month externally, or use
`defaultMonthKey` and let the placeholder manage its internal month state while
still receiving navigation callbacks.

Use `onDaySelect` to react when users click a day; the handler receives both the
ISO date string and the corresponding `Date` instance so consuming apps can hook
up modals, drawers, or detail views.

Inject custom day rendering with the `renderDay` prop—see `example/App.tsx` for
placeholder images loaded from placehold.co while the real thumbnail
stack is still under construction.

Once the component architecture stabilizes, this folder can be promoted into a
stand-alone repository without significant changes—package metadata already
assumes an eventual npm distribution.
