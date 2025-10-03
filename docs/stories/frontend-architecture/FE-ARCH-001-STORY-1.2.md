# Story 1.2: Update TypeScript Configuration

**Epic**: [FE-ARCH-001: Foundation Setup](../../epics/FE-ARCH-001-FOUNDATION-SETUP.md)  
**Story ID**: FE-ARCH-001-STORY-1.2  
**Story Points**: 0.5  
**Priority**: P0 - Critical  
**Status**: Ready  

---

## User Story

**As a** frontend developer  
**I want** TypeScript path aliases configured  
**So that** I can use clean imports like `@/features/auth`

---

## Acceptance Criteria

1. ✅ `tsconfig.json` updated with path aliases
2. ✅ Path aliases work in development
3. ✅ Path aliases work in production builds
4. ✅ IDE autocomplete works with new paths
5. ✅ No existing imports broken

---

## Technical Implementation

### Update tsconfig.json

```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"],
      "@/features/*": ["./src/features/*"],
      "@/components/*": ["./src/components/*"],
      "@/lib/*": ["./src/lib/*"],
      "@/routes/*": ["./src/routes/*"]
    }
  }
}
```

### Validation Code

```typescript
// Test file: src/test-imports.ts (temporary)
import { Button } from '@/components/ui/button'
import { validateEmail } from '@/lib/validations'
// These should work once aliases are configured

// Delete this file after verification
```

---

## Tasks

- [ ] Open `web/tsconfig.json`
- [ ] Add `baseUrl: "."` to compilerOptions
- [ ] Add `paths` object with all aliases
- [ ] Save file
- [ ] Restart TypeScript server in IDE
- [ ] Create test import file
- [ ] Verify TypeScript compilation succeeds
- [ ] Verify IDE autocomplete works
- [ ] Delete test file
- [ ] Run full build
- [ ] Commit changes

---

## Definition of Done

- [ ] `tsconfig.json` updated with correct paths
- [ ] TypeScript compiler accepts new paths
- [ ] IDE shows autocomplete for `@/features/*`
- [ ] IDE shows autocomplete for `@/components/*`
- [ ] IDE shows autocomplete for `@/lib/*`
- [ ] `npm run build` succeeds
- [ ] `npm run dev` works with new paths
- [ ] No TypeScript errors introduced
- [ ] Changes committed to git

---

## Testing

### Manual Testing
1. Update tsconfig.json
2. Restart TypeScript server (VSCode: Cmd+Shift+P → "Restart TS Server")
3. Create test file with imports
4. Verify autocomplete works
5. Verify no red squiggles
6. Run build

### Commands
```bash
# Type check
npm run type-check

# Build
npm run build

# Dev
npm run dev
```

---

## Dependencies

**Requires**: Story 1.1 (Features directory created)

**Blocks**: Story 1.3 (Vite config)

---

**Related ADR**: [ADR-011: Frontend File Architecture](../../architecture/adr/ADR-011-FRONTEND-FILE-ARCHITECTURE.md)  
**Epic**: [FE-ARCH-001: Foundation Setup](../../epics/FE-ARCH-001-FOUNDATION-SETUP.md)
