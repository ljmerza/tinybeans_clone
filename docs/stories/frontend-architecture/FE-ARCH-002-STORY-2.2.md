# Story 2.2: Migrate API Client and Store

**Epic**: [FE-ARCH-002: Auth Migration](../../epics/FE-ARCH-002-AUTH-MIGRATION.md)  
**Story ID**: FE-ARCH-002-STORY-2.2  
**Story Points**: 1  
**Status**: Blocked (Story 2.1)  

## User Story
**As a** frontend developer  
**I want** auth API client and store in the features directory  
**So that** auth data management is co-located

## Acceptance Criteria
1. ✅ `authClient.ts` moved and working
2. ✅ `authStore.ts` moved and working
3. ✅ All imports updated
4. ✅ TypeScript types properly imported
5. ✅ No functionality broken

## Tasks
- [ ] Move `features/auth/client.ts` to `features/auth/api/authClient.ts`
- [ ] Move `features/auth/store.ts` to `features/auth/store/authStore.ts`
- [ ] Move `features/auth/types.ts` to `features/auth/types/auth.types.ts`
- [ ] Update imports in `main.tsx`
- [ ] Update imports in `App.tsx`
- [ ] Update imports in `PublicOnlyRoute.tsx`
- [ ] Test auth flows
- [ ] Commit changes

**Related ADR**: [ADR-011](../../architecture/adr/ADR-011-FRONTEND-FILE-ARCHITECTURE.md)
