# Story 2.6: Migrate Logout and Auth Utilities

**Epic**: [FE-ARCH-002: Auth Migration](../../epics/FE-ARCH-002-AUTH-MIGRATION.md)  
**Story ID**: FE-ARCH-002-STORY-2.6  
**Story Points**: 0.5  
**Status**: Blocked (Story 2.5)  

## User Story
**As a** frontend developer  
**I want** logout and utility functions in the auth feature  
**So that** all auth code is co-located

## Acceptance Criteria
1. ✅ `LogoutHandler` component created
2. ✅ `useLogout` hook created
3. ✅ `useAuthCheck` hook migrated
4. ✅ `AuthDevtools` component migrated
5. ✅ All utilities working

## Tasks
- [ ] Create LogoutHandler component
- [ ] Create useLogout hook
- [ ] Migrate useAuthCheck hook
- [ ] Migrate AuthDevtools component
- [ ] Update routes/logout.tsx
- [ ] Export from index
- [ ] Test logout flow
- [ ] Commit changes

**Related ADR**: [ADR-011](../../architecture/adr/ADR-011-FRONTEND-FILE-ARCHITECTURE.md)
