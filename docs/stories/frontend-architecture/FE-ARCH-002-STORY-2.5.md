# Story 2.5: Migrate Magic Link Components

**Epic**: [FE-ARCH-002: Auth Migration](../../epics/FE-ARCH-002-AUTH-MIGRATION.md)  
**Story ID**: FE-ARCH-002-STORY-2.5  
**Story Points**: 1.5  
**Status**: Blocked (Story 2.4)  

## User Story
**As a** frontend developer  
**I want** magic link functionality in the auth feature  
**So that** all auth methods are co-located

## Acceptance Criteria
1. ✅ `MagicLinkForm` component created
2. ✅ `MagicLoginHandler` component created
3. ✅ `useMagicLink` hooks created
4. ✅ Route files updated
5. ✅ Magic link flow working end-to-end

## Tasks
- [ ] Create MagicLinkForm component
- [ ] Create MagicLoginHandler component
- [ ] Create useMagicLink hook
- [ ] Update routes/magic-link-request.tsx
- [ ] Update routes/magic-login.tsx
- [ ] Export from index
- [ ] Test full magic link flow
- [ ] Commit changes

**Related ADR**: [ADR-011](../../architecture/adr/ADR-011-FRONTEND-FILE-ARCHITECTURE.md)
