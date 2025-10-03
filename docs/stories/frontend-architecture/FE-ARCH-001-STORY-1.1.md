# Story 1.1: Create Features Directory Structure

**Epic**: [FE-ARCH-001: Foundation Setup](../../epics/FE-ARCH-001-FOUNDATION-SETUP.md)  
**Story ID**: FE-ARCH-001-STORY-1.1  
**Story Points**: 0.5  
**Priority**: P0 - Critical  
**Status**: Ready  

---

## User Story

**As a** frontend developer  
**I want** a standardized `features/` directory structure  
**So that** I know where to place feature-specific code

---

## Acceptance Criteria

1. ✅ `src/features/` directory created with README
2. ✅ Template subdirectory structure documented
3. ✅ Structure doesn't break existing builds
4. ✅ Directory structure follows naming conventions
5. ✅ Documentation explains when to use features vs components

---

## Technical Implementation

### Directory Structure to Create

```bash
web/src/
└── features/
    ├── README.md               # Documents feature organization
    ├── .gitkeep                # Ensures directory is tracked
    └── _template/              # Template for new features
        ├── index.ts            # Public exports
        ├── components/
        │   └── .gitkeep
        ├── hooks/
        │   └── .gitkeep
        ├── api/
        │   └── .gitkeep
        ├── types/
        │   └── .gitkeep
        └── utils/
            └── .gitkeep
```

### README.md Content

```markdown
# Features Directory

This directory contains feature modules organized using a feature-based architecture pattern.

## What is a Feature?

A feature is a self-contained module that encapsulates related functionality:
- 3+ related components
- Dedicated business logic
- Represents a distinct domain concept
- Used across multiple routes

## Feature Structure

Each feature follows this standard structure:

\`\`\`
feature-name/
├── index.ts              # Public API exports
├── components/           # Feature-specific components
├── hooks/                # Custom React hooks
├── api/                  # API client functions
├── types/                # TypeScript definitions
└── utils/                # Feature-specific utilities
\`\`\`

## Naming Conventions

- Features: `lowercase-with-dashes` (e.g., `user-profile`)
- Components: `PascalCase.tsx` (e.g., `UserProfile.tsx`)
- Hooks: `camelCase.ts` with 'use' prefix (e.g., `useUserProfile.ts`)
- Types: `PascalCase` (e.g., `UserProfileData`)

## Import Patterns

✅ **Good**: `import { LoginForm } from '@/features/auth'`  
❌ **Bad**: `import { LoginForm } from '@/features/auth/components/LoginForm'`

Always import from the feature's index.ts file.

## When to Create a Feature vs Component

**Create a Feature when:**
- Contains 3+ related components
- Has dedicated business logic
- Represents a domain concept (auth, profile, settings)
- Will be used across multiple routes

**Create a Shared Component when:**
- Used across multiple features
- Pure UI component with no business logic
- Generic utility component (buttons, modals, etc.)

## Examples

See existing features:
- `auth/` - Authentication feature
- `twofa/` - Two-factor authentication feature
```

---

## Tasks

- [ ] Create `src/features/` directory
- [ ] Create `src/features/.gitkeep` file
- [ ] Create `src/features/README.md` with documentation
- [ ] Create `src/features/_template/` directory
- [ ] Create template subdirectories (components, hooks, api, types, utils)
- [ ] Add `.gitkeep` files to template subdirectories
- [ ] Create template `index.ts` with example exports
- [ ] Run `npm run build` to verify no breakage
- [ ] Commit changes

---

## Definition of Done

- [ ] Directory structure created exactly as specified
- [ ] README.md written and reviewed
- [ ] Template directory complete with all subdirectories
- [ ] Build succeeds (`npm run build`)
- [ ] Dev server starts (`npm run dev`)
- [ ] No existing functionality broken
- [ ] Changes committed to git
- [ ] Story reviewed and approved

---

## Testing

### Manual Testing
1. Navigate to `src/features/` directory
2. Verify README.md is readable and clear
3. Verify template structure is complete
4. Run `npm run build` - should succeed
5. Run `npm run dev` - should start without errors

### Validation
```bash
# Verify structure
ls -la src/features/
ls -la src/features/_template/

# Verify build
npm run build

# Verify dev server
npm run dev
```

---

## Dependencies

**Blocks**: All other Epic 1 stories

**Blocked By**: None

---

## Notes

- This is a purely additive change - no existing code is modified
- The directory structure follows the pattern defined in ADR-011
- Template will be used by the feature generator in Epic 4

---

**Related ADR**: [ADR-011: Frontend File Architecture](../../architecture/adr/ADR-011-FRONTEND-FILE-ARCHITECTURE.md)  
**Epic**: [FE-ARCH-001: Foundation Setup](../../epics/FE-ARCH-001-FOUNDATION-SETUP.md)
