# Story 2.4: Extract and Migrate Signup Components

**Epic**: [FE-ARCH-002: Auth Migration](../../epics/FE-ARCH-002-AUTH-MIGRATION.md)  
**Story ID**: FE-ARCH-002-STORY-2.4  
**Story Points**: 2  
**Status**: Blocked (Story 2.3)  

## User Story
**As a** frontend developer  
**I want** signup components extracted from route files  
**So that** signup logic is reusable and well-organized

## Acceptance Criteria
1. ✅ `SignupForm` component created
2. ✅ `useSignup` hook created
3. ✅ `routes/signup.tsx` updated
4. ✅ Signup flow working correctly
5. ✅ Email verification flow working

## Tasks
- [ ] Extract SignupForm component
- [ ] Create `features/auth/components/SignupForm.tsx`
- [ ] Extract useSignup hook
- [ ] Create `features/auth/hooks/useSignup.ts`
- [ ] Update `routes/signup.tsx`
- [ ] Export from index
- [ ] Test signup flow
- [ ] Commit changes

**Related ADR**: [ADR-011](../../architecture/adr/ADR-011-FRONTEND-FILE-ARCHITECTURE.md)
