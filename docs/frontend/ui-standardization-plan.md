# UI Standardization Plan

## Objectives
- Establish a cohesive UI system so product teams can ship screens quickly without re-inventing layout, form, or feedback patterns.
- Reduce visual drift by auditing existing components, consolidating on shared primitives, and removing ad-hoc Tailwind class clusters.
- Document migration paths and design guardrails so new UI stays aligned with the design tokens defined in `web/src/styles.css`.

## Current UI Landscape
- **Design tokens & utilities** — `web/src/styles.css` defines color tokens, typography helpers (`heading-*`, `text-*`), containers, and form utility classes that are partially adopted.
- **Shared primitives** — `@/components/ui` contains shadcn-based elements (`button`, `input`, `label`, `select`, `slider`, `switch`, `tabs`, `textarea`, `alert-dialog`, `badge`, `confirm-dialog`) plus composable wrappers such as `ButtonGroup`, `Card`, `Chip`, `StatusMessage`, `InfoPanel`, `FormField`, `FormActions`, `LoadingSpinner`, `StandardError`, and the consolidated `LoadingState`.
- **Feature-specific wrappers** — Auth and Circles experiences rely on higher-order layouts (`AuthCard`, `Wizard`, `Layout`, `Header`) that mix shared primitives with bespoke spacing.
- **Observed drift** — Legacy `.btn-*` utilities, duplicated empty/loader states, mixed usage of `Chip` versus `Badge`, and inline `div` structures for form helper text cause inconsistency across routes.

## Standardization Targets

### Buttons & Click Targets
- Reference `docs/frontend/button-standardization-plan.md` as the canonical action plan.
- Expand the effort to cover `ButtonGroup`, link-as-button usage, icon-only triggers, pagination controls, and destructive confirmations so every interactive element consumes `@/components/ui/button`.
- Track down residual `<button>` or `<Link>` instances that still rely on Tailwind utilities and migrate them during the final clean-up pass.
- Encourage teams to leverage the shared `Button` component's `isLoading` prop instead of embedding bespoke spinner markup inside buttons.

### Form Inputs & Validation
- Consolidate on `FormField`, `FieldError`, `FormActions`, and shadcn inputs (`input`, `select`, `textarea`, `switch`, `slider`).
- Build `FormField` variations for checkbox/radio groups and date/time pickers; expose layout presets (stacked, inline, compact) with class-variance-authority.
- Replace inline helper/error markup in feature forms (auth, 2FA, circles) with the shared wrappers and ensure `aria-*` wiring is consistent.
- Publish a usage guide covering TanStack Form integration, status messaging, and recommended spacing; add Storybook stories for happy/error states.

### Feedback & Messaging
- Normalize transient feedback through `showToast` in `web/src/lib/toast.ts` by defining toast variants, icons, and durations in one place.
- Provide a shared `Alert`/`Banner` component that wraps `StatusMessage` and `InfoPanel` patterns for inline messaging (success, warning, info, error).
- Audit pages that render raw `<p>` tags for success/error text and convert them to the shared feedback components.
- Document guidance on when to use toasts versus inline messaging, and ensure translations map to consistent variants.

### Layout & Navigation
- Finalize `Layout` and `Header` as the default shell for authenticated screens; extract navigation link data to a config object for easier customization.
- Standardize page containers (`container-page`, `container-narrow`, `container-sm`) and section spacing utilities so features stop redefining padding.
- Introduce a secondary layout for settings/detail pages (sidebar, breadcrumbs) if upcoming work demands it, reusing global tokens.
- Document layout patterns for marketing-style landing pages versus application workflows, clarifying when to hide the header or use `AuthCard`.

### Loading, Empty, and Error States
- Adopt the consolidated `LoadingState` component for inline, section, and full-screen scenarios, replacing residual ad-hoc spinners.
- Align `StandardError`, `ErrorBoundary`, and route-level fallback UI so they share typography, icons, and button variants.
- Create an `EmptyState` component (illustration, title, description, primary/secondary actions) and catalogue existing call sites that roll their own placeholders.
- Capture Playwright or Storybook visual baselines for loading/error/empty states to guard against regressions during refactors.

### Overlays, Dialogs, and Confirmations
- Ensure all modals and confirmation flows consume `@/components/ui/dialog` or `@/components/ui/confirm-dialog` with consistent focus traps, sizing, and keyboard behaviour.
- Provide preset layouts for destructive confirmations, multi-step modals, and form-in-modal scenarios, backed by shared spacing tokens.
- Add linting or codemods to catch raw Radix usage so teams reach for the sanctioned wrappers instead.
- Write documentation covering accessibility expectations (aria labels, focus return, escape handling) and cross-link it from the engineering handbook.

### Data Display Components
- Clarify the roles of `Chip` versus `Badge` and decide whether to converge on one token-driven component with variants for status, filter, and count displays.
- Inventory tables, list rows, and key-value summaries in the routes to determine if shared `Table`, `DescriptionList`, or `ListItem` primitives are warranted.
- Expand `Card` with header/footer helpers, hover states, and layout presets (metric card, media card) to replace bespoke class strings.
- Publish compositional examples combining `Card`, `Chip`, `Badge`, and typography helpers so teams can assemble dashboards and detail pages rapidly.

### Complex Flows & Wizards
- Formalize the `Wizard` API for multi-step onboarding: document how to structure steps, surface progress indicators, and integrate with form validation.
- Create reusable step indicators (progress bar, stepper) and align `ButtonGroup` usage for next/back/skip actions.
- Provide guidance for server-driven flows (conditional steps) and error recovery within the wizard framework.

### Typography & Spacing Standards
- Promote the `heading-*`, `text-*`, `link`, `container-*`, and `section-spacing*` utilities as the default typographic scale.
- Identify views that override font sizes or weights with arbitrary Tailwind tokens and migrate them to the shared scale.
- Document responsive behaviour and dark-mode expectations tied to the tokens defined in `web/src/styles.css`.
- Add lint rules or a documentation checklist to discourage hard-coded pixel values when utilities exist.

### Accessibility & Internationalization
- Bake aria attributes, keyboard interactions, and focus management into the shared components, documenting do/don't examples.
- Ensure each component has i18n-friendly defaults (no hard-coded English copy) and supports RTL layouts if required.
- Provide a11y testing guidance (axe, jest-axe, manual keyboard checks) as part of the adoption playbook.

## Implementation Phases
1. **Foundation (Week 0-1)** — Confirm design token catalog, audit existing components, and align with design/PM on the target component list. Finalize the button plan as baseline.
2. **Core Primitives (Week 2-4)** — Ship standardized buttons, inputs, form wrappers, and feedback components. Add Storybook coverage and documentation.
3. **Layouts & States (Week 5-6)** — Harmonize layouts, loading/error/empty states, and overlay patterns. Introduce utility linting where feasible.
4. **Advanced Patterns (Week 7-8)** — Roll out data display modules, wizard enhancements, and any remaining specialized components. Backfill tests and visual baselines.
5. **Migration & Cleanup (Continuous)** — Track adoption with a migration board, remove legacy utilities (`.btn-*`, bespoke helper divs), and enforce usage via code review checklists.

## Tooling & Documentation
- Stand up a Storybook or Ladle environment to demo each component state alongside accessibility notes.
- Add Vitest/Testing Library examples that show recommended testing patterns for form validation, toasts, and dialog interactions.
- Extend linting (ESLint, custom lint rules) to flag raw HTML buttons, ad-hoc headings, or unsupported class names.
- Maintain a changelog in `docs/frontend` so design and engineering stay aligned on component evolutions.

## Next Actions
1. **Design leadership alignment**
   - Produce a one-page synopsis (objectives, phases, key dependencies) and circulate it with design leadership ahead of a 30-minute review.
   - Host the review to confirm priority order for component families, capture feedback in meeting notes, and update this plan with any scope adjustments.
   - Record an explicit sign-off (Slack thread or doc comment) so downstream teams know the plan is approved.
2. **Button variance close-out**
   - Audit remaining `ButtonGroup`, link-as-button, icon-only, pagination, and destructive confirmation use-cases that still bypass `@/components/ui/button`.
   - Implement or extend button variants and supporting props, update Storybook stories, and ensure tests cover primary error/destructive paths.
   - File cleanup tickets for stubborn call sites that require coordination with feature teams and track them on the migration board.
3. **Form-field deep dive**
   - Inventory forms in auth, 2FA, circles, and settings to catalogue missing primitives (checkbox/radio clusters, date/time pickers) and layout patterns.
   - Draft a component spec for new `FormField` variants (stacked, inline, compact) including accessibility requirements and TanStack Form integration notes.
   - Build the new primitives behind a feature flag, write Vitest + Testing Library coverage for validation states, and publish Storybook examples (happy/error/loading).
4. **Unified loading/error/empty prototypes**
   - Align with design on shared visuals and copy guidelines for loading, empty, and error states (icons, typography, spacing, CTA patterns).
   - Create consolidated `LoadingState`, `ErrorState`, and `EmptyState` components with configurable density (inline vs. page) and wire them into Storybook + docs.
   - Pilot the components in two high-traffic routes (e.g., dashboard and circles) to validate API ergonomics before broader rollout.
5. **Duplicated UI inventory**
   - Use repository searches (e.g., `rg` on `.btn-`, custom helper divs) to find duplicated patterns in `profile`, `twofa`, `circles`, and related routes.
   - Capture findings in a migration log (source file, recommended primitive, blockers) and open tickets that bundle similar refactors for sprint planning.
   - Partner with feature owners to sequence migrations around active roadmap work so refactors do not collide with new features.
6. **Enforcement standards**
   - Draft additions to the engineering review checklist covering buttons, form wrappers, feedback messaging, and layout utilities.
   - Propose ESLint or custom lint rules that catch raw HTML buttons, ad-hoc headings, and unsanctioned class clusters; validate them against the current codebase.
   - Update developer documentation (handbook, onboarding materials) and run a brown-bag session to walk through the new guardrails.
