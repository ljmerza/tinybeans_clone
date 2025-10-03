# Story 1.3: Update Vite Build Configuration

**Epic**: [FE-ARCH-001: Foundation Setup](../../epics/FE-ARCH-001-FOUNDATION-SETUP.md)  
**Story ID**: FE-ARCH-001-STORY-1.3  
**Story Points**: 0.5  
**Priority**: P0 - Critical  
**Status**: Ready  

---

## User Story

**As a** frontend developer  
**I want** Vite configured with path aliases  
**So that** builds resolve imports correctly

---

## Acceptance Criteria

1. ✅ `vite.config.ts` updated with resolve aliases
2. ✅ Development server resolves new paths
3. ✅ Production builds resolve new paths
4. ✅ Hot module reload works with new structure
5. ✅ Build performance not degraded

---

## Technical Implementation

```typescript
// web/vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@/features': path.resolve(__dirname, './src/features'),
      '@/components': path.resolve(__dirname, './src/components'),
      '@/lib': path.resolve(__dirname, './src/lib'),
      '@/routes': path.resolve(__dirname, './src/routes'),
    },
  },
})
```

---

## Tasks

- [ ] Open `web/vite.config.ts`
- [ ] Import `path` module
- [ ] Add `resolve.alias` configuration
- [ ] Save file
- [ ] Restart dev server
- [ ] Create test component with imports
- [ ] Verify HMR works
- [ ] Build production bundle
- [ ] Check bundle size
- [ ] Verify source maps work
- [ ] Delete test component
- [ ] Commit changes

---

## Definition of Done

- [ ] `vite.config.ts` updated correctly
- [ ] Dev server starts without errors
- [ ] Production build succeeds
- [ ] HMR works with new paths
- [ ] Bundle size within 5% of current
- [ ] Source maps work correctly
- [ ] No build warnings
- [ ] Changes committed

---

## Testing

```bash
# Clean and rebuild
rm -rf node_modules/.vite
npm run dev

# Production build
npm run build

# Check bundle size
ls -lh dist/assets/
```

---

## Dependencies

**Requires**: Story 1.2 (TypeScript config)

**Blocks**: Story 1.4 (Feature template)

---

**Related ADR**: [ADR-011: Frontend File Architecture](../../architecture/adr/ADR-011-FRONTEND-FILE-ARCHITECTURE.md)  
**Epic**: [FE-ARCH-001: Foundation Setup](../../epics/FE-ARCH-001-FOUNDATION-SETUP.md)
