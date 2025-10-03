# Story 2.7: Update All Imports and Clean Up

**Epic**: [FE-ARCH-002: Auth Migration](../../epics/FE-ARCH-002-AUTH-MIGRATION.md)  
**Story ID**: FE-ARCH-002-STORY-2.7  
**Story Points**: 0.5  
**Status**: Blocked (Story 2.6)  

## User Story
**As a** frontend developer  
**I want** all imports updated to use the new feature structure  
**So that** the old module directory can be removed

## Acceptance Criteria
1. ✅ All imports updated across entire codebase
2. ✅ No references to `features/auth/*` remain
3. ✅ All TypeScript errors resolved
4. ✅ All linting errors resolved
5. ✅ Old `features/auth/` directory removed

## Tasks
- [ ] Run import migration script
- [ ] Find all @/features/auth references
- [ ] Update to @/features/auth
- [ ] Test all auth flows
- [ ] Run linter
- [ ] Run type check
- [ ] Remove features/auth directory
- [ ] Commit changes

**Related ADR**: [ADR-011](../../architecture/adr/ADR-011-FRONTEND-FILE-ARCHITECTURE.md)
