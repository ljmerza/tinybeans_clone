# Story 2.3: Extract and Migrate Login Components

**Epic**: [FE-ARCH-002: Auth Migration](../../epics/FE-ARCH-002-AUTH-MIGRATION.md)  
**Story ID**: FE-ARCH-002-STORY-2.3  
**Story Points**: 2  
**Status**: Blocked (Story 2.2)  

## User Story
**As a** frontend developer  
**I want** login components extracted from route files  
**So that** routes are thin and components are reusable

## Acceptance Criteria
1. ✅ `LoginForm` component created in `features/auth/components/`
2. ✅ `useLogin` hook created in `features/auth/hooks/`
3. ✅ `routes/login.tsx` updated to use extracted components
4. ✅ Login flow working correctly
5. ✅ All validations and error handling preserved

## Tasks
- [ ] Extract LoginForm component from routes.login.tsx
- [ ] Create `features/auth/components/LoginForm.tsx`
- [ ] Extract useLogin hook
- [ ] Create `features/auth/hooks/useLogin.ts`
- [ ] Update `routes/login.tsx` to use new components
- [ ] Export from `features/auth/index.ts`
- [ ] Test login flow
- [ ] Commit changes

**Related ADR**: [ADR-011](../../architecture/adr/ADR-011-FRONTEND-FILE-ARCHITECTURE.md)
