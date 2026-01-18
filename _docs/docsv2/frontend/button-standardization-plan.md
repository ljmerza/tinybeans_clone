# Button Standardization Plan

## Goals
- Deliver a single, composable button system that covers primary CTAs, secondary/supporting actions, lightweight text links, icon-only triggers, and destructive flows.
- Remove legacy `.btn-*` utility classes from Tailwind layers and replace ad‑hoc `<button>` markup with the shared `Button` component (or approved wrappers) to ensure consistent tokens, focus states, and accessibility.
- Document migration steps so feature teams can incrementally adopt the standard without blocking in-flight work.

## Current Button Inventory
- `@/components/ui/button` — shadcn-style primitive that already exposes `variant` (`default`, `destructive`, `outline`, `secondary`, `ghost`, `link`) and `size` (`sm`, `default`, `lg`, `icon`) via `cva`.
- `@/components/ButtonGroup` — flex wrapper that manages spacing, alignment, and optional wrapping for clusters of actions.
- `@/features/auth/oauth/GoogleOAuthButton` — branded wrapper around the base `Button` with Google-specific styling and iconography.
- Legacy Tailwind utilities in `web/src/styles.css` (`.btn-primary`, `.btn-secondary`, `.btn-ghost`, `.btn-danger`) used directly on `<button>` and `<Link>` elements.

## Audit: Non-standard Usage
The following files currently bypass the shared `Button` primitive or rely on legacy `btn-*` classes. Items under `route-views/` mirror `routes/` and will require the same fix.

| File | Pattern | Notes |
| --- | --- | --- |
| `web/src/components/ErrorBoundary.tsx:53` | `<button className="btn-primary">` | Should use `Button` (likely `variant="primary"` once defined) with navigation handler. |
| `web/src/components/StandardError.tsx:39` | `<button className="btn-primary">` | Replace with `Button` and allow variant override via prop. |
| `web/src/components/Header.tsx:23,26,29,43,46` | `<Link className="btn-*">` | Convert to `Button` with `asChild` so `Link` adopts shared styles. |
| `web/src/routes/profile/2fa/index.tsx:199` | `<button className="text-sm …">` | Back-to-home action; use `Button` with `variant="ghost"`/`link`. |
| `web/src/routes/profile/2fa/trusted-devices.tsx:150` | `<button className="text-sm …">` | Navigation action; should leverage `Button` link-style variant. |
| `web/src/routes/profile/2fa/verify.tsx:116,195` | `<button className="text-sm …">` | Footer navigation + toggle between code types; convert to shared variants. |
| `web/src/features/twofa/components/RecoveryCodeList.tsx:82` | `<button …>` per recovery code | Replace with `Button` (`variant="ghost"`/`outline`) or reconsider semantic element (maybe `<li>` with `Button` child). |
| `web/src/routes/profile/2fa/trusted-devices.tsx` (and `verify.tsx`, `index.tsx`) | duplicates under `web/src/route-views/**` | Mirror updates after main routes migrate. |
| `web/src/styles.css:88-115` | `.btn-*` utility definitions | Marked for removal once replacements ship to avoid drift. |

No additional bespoke `Button` components were discovered (`rg -g '*Button.tsx' web/src`), so consolidating on the shared primitive should cover the entire surface area.

## Target Button Variants & Sizes
- **Primary** (`variant="primary"`; defaults to CTA) — solid fill using `--primary`, high contrast text, supports loading and disabled states.
- **Secondary** (`variant="secondary"`) — filled but lower emphasis; map to `--secondary`.
- **Tertiary / Ghost** (`variant="ghost"`) — minimal chrome for inline actions; consider optional background on hover only.
- **Outline** (`variant="outline"`) — bordered neutral option for cancel/secondary actions.
- **Destructive** (`variant="destructive"`) — dangerous actions with stronger focus ring and motion feedback.
- **Success / Positive** (`variant="success"`; new) — confirmatory actions (e.g., save) if design needs a green state.
- **Link** (`variant="link"`) — text link styling for inline navigation buttons.
- **Icon** (`size="icon"`) — square button for icon-only interactions; allow combination with above variants.
- **Branded** (`variant="brand-google"` + icon slot) — optional slot-based theming instead of bespoke wrapper, or keep `GoogleOAuthButton` as thin wrapper around new variant.
- Sizes: retain `sm`, `default`, `lg`, `icon`; evaluate `xl` marketing need. Document spacing, min-width rules, and icon alignment for each.

State handling enhancements to bake into the primitive:
- `isLoading` prop that renders a spinner (re-use `LoadingSpinner`) and sets `aria-busy`.
- Loading + disabled share visual treatment but keep focus outlines once the interaction completes.
- `aria-invalid` styling already baked in; extend to show consistent border + ring on error.
- Ensure `focus-visible` and keyboard interactions meet WCAG contrast.

## Implementation Roadmap
1. **Design & Token Alignment**
   - Confirm color tokens for new variants (`success`, branded) with design.
   - Update `buttonVariants` map in `@/components/ui/button` and expose new props (`isLoading`, `iconPosition` if needed).
2. **Documentation & Examples**
   - Author Storybook stories or MDX usage guide showing each variant, size, state, and composition inside `ButtonGroup`.
   - Add developer notes covering `asChild` usage for `Link` and form submissions.
3. **Migration**
   - Replace legacy `.btn-*` usages with the standardized `Button` API (`ErrorBoundary`, `StandardError`, `Header` nav links).
   - Update navigation/toggle buttons in 2FA routes (`routes/` and mirrored `route-views/`) to use `Button` variants.
   - Refine `RecoveryCodeList` interactions (decide between `Button` or semantic list item with `Button` child).
   - Ensure `GoogleOAuthButton` consumes new `brand-google` variant or re-export `Button` with preset props.
4. **Clean-up**
   - After all consumers migrate, remove `.btn-*` utilities from `styles.css` to prevent backslide.
   - Run Tailwind purge/analysis to confirm no unused classes remain.
5. **QA & Regression Testing**
   - Capture Chromatic/Playwright visual snapshots for primary views (auth flows, header, 2FA screens).
   - Add unit/Storybook interaction tests verifying loading states, disabled behaviour, and keyboard focus.

## Risks & Mitigations
- **Unknown third-party styles** — Search for `.btn-` usage during migration to avoid regressions.
- **Branded buttons** — Validate Google OAuth compliance when switching to standardized variant; keep dedicated component if guidelines require bespoke dims.
- **Duplicated routes** — Ensure both `routes/` and `route-views/` folders stay in sync to avoid hydration mismatches.

## Next Actions
1. Align on final variant palette with design/PM.
2. Extend `Button` component API (`isLoading`, additional variants) and document usage.
3. Refactor identified files to consume standardized variants.
4. Remove legacy `.btn-*` styles once refs are gone.
