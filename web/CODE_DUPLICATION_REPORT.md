# Code Duplication Report - Web Project

**Last Updated:** December 2024  
**Scope:** `/web/src` directory

## Executive Summary

This report tracks code duplication patterns in the web project. Items are organized by completion status and priority.

**Status Overview:**
- ✅ **7 items completed** (~790 LOC eliminated)
- 🔄 **3 items remaining** (~80 LOC potential savings)

---

## ✅ Completed Fixes

The following duplications have been successfully resolved:

### 1. ✅ **Confirm Dialog Components** (COMPLETED)
- **Removed:** `confirm-dialog-with-content.tsx`
- **Result:** Consolidated into single `ConfirmDialog` component with optional `children` prop
- **LOC Saved:** ~150 lines
- **Date:** December 2024

### 2. ✅ **App.tsx vs Layout.tsx Header Duplication** (COMPLETED)
- **Created:** Shared `Header` component
- **Removed:** Unused `App.tsx` file
- **Result:** Single source of truth for header navigation
- **LOC Saved:** ~30 lines
- **Date:** December 2024

### 3. ✅ **QueryClient Configuration Duplication** (COMPLETED)
- **Removed:** `integrations/tanstack-query/root-provider.tsx` (unused file)
- **Result:** Single QueryClient instance in `main.tsx`
- **LOC Saved:** ~40 lines
- **Date:** December 2024

### 4. ✅ **Login Card Components** (COMPLETED)
- **Removed:** `ModernLoginCard.tsx` (duplicate)
- **Result:** Consolidated into `LoginCard.tsx` with ADR-012 compliance
- **LOC Saved:** ~200 lines
- **Date:** December 2024

### 5. ✅ **2FA Setup Wizard Steps** (COMPLETED)
- **Created:** Generic step components (IntroStep, VerifyStep, RecoveryStep)
- **Updated:** 9 step files to use generic components
- **Result:** Reusable wizard patterns with configuration-based approach
- **LOC Saved:** ~193 lines
- **Date:** December 2024

### 6. ✅ **2FA Method Cards** (COMPLETED)
- **Created:** `GenericMethodCard` component
- **Updated:** 3 method cards to use generic component
- **Result:** Consistent card UI with configuration objects
- **LOC Saved:** ~161 lines
- **Date:** December 2024

### 7. ✅ **API Response Interface Duplication** (COMPLETED)
- **Created:** `src/types/api.ts` with shared `ApiMessage` and `ApiResponse` types
- **Updated:** 3 files to import from shared types
- **Result:** Single source of truth for API types with comprehensive documentation
- **LOC Saved:** ~15-20 lines
- **Date:** December 2024

**Total Completed:** ~790 lines of duplicate code eliminated, 16+ files removed/consolidated

---

## Minor Duplications (Low Priority)

These remain as potential improvements but have lower impact:

### 8. **Error Handling Patterns** 🔷 LOW PRIORITY

**Location:**
Multiple locations in auth and 2FA features

**Issue:** Repeated error handling pattern:
```typescript
catch (err) {
  const apiMessage = (err as { data?: { error?: string } })?.data?.error;
  // handle error
}
```

**Occurrences:**
- `src/routes/2fa/settings.tsx` (2 times)
- `src/routes/2fa/setup/index.tsx` (1 time)

**Recommended Fix:**
Create error handling utility function.

**Estimated LOC Reduction:** ~20 lines

---

### 9. **2FA Navigation State** 🔷 LOW PRIORITY

**Location:**
- `src/features/auth/hooks/modernHooks.ts`
- `src/features/auth/hooks/index.ts` (2 times)

**Issue:** Repeated 2FA navigation logic:
```typescript
if (data.requires_2fa) {
  const state: TwoFactorNavigateState = {
    partialToken: data.partial_token,
    method: data.method,
    message: data.message,
  };
  navigate({ to: '/2fa/verify', state });
}
```

**Recommended Fix:**
Extract to utility function `handleTwoFactorRedirect()`.

**Estimated LOC Reduction:** ~15 lines

---

### 10. **Message Display Pattern** 🔷 LOW PRIORITY

**Location:**
Multiple auth hooks

**Issue:** Repeated pattern:
```typescript
if (data?.messages) {
  showAsToast(data.messages, 200);
}
```

**Occurrences:** 4 times in `modernHooks.ts`, 3 times in `oauth/hooks.ts`

**Recommended Fix:**
Consider if this should be handled at a higher level (interceptor) or extracted to a utility.

**Estimated LOC Reduction:** ~10 lines

---

## Summary Statistics

| Status | Priority | Category | Count | LOC Reduction |
|--------|----------|----------|-------|---------------|
| ✅ Done | HIGH | Component Duplication | 3 | ~190 lines |
| ✅ Done | MEDIUM | Similar Components | 3 | ~555 lines |
| ✅ Done | LOW | Type Definitions | 1 | ~15 lines |
| 🔄 Remaining | LOW | Code Patterns | 3 | ~45 lines |
| **TOTAL COMPLETED** | | | **7** | **~790 lines** |
| **TOTAL REMAINING** | | | **3** | **~45 lines** |

---

## Recommendations

### Completed ✅
1. ✅ Confirm Dialog Components - Merged into single flexible component
2. ✅ Header Components - Created shared Header component
3. ✅ QueryClient Configuration - Removed unused file
4. ✅ Login Card Components - Consolidated into one component
5. ✅ 2FA Setup Wizard Steps - Created generic reusable components
6. ✅ 2FA Method Cards - Created generic card component
7. ✅ API Response Types - Centralized in src/types/

### Optional Future Improvements (Low Priority)
8. Extract error handling utilities for common patterns
9. Extract 2FA navigation logic
10. Review message display centralization

---

## Architecture Improvements Completed

### Component Consolidation
- **Confirm Dialogs:** 2 files → 1 unified component
- **Header:** Extracted shared component, removed duplicate
- **Login Cards:** 2 files → 1 with better docs
- **2FA Setup Steps:** 9 duplicate files → 3 generic + 9 thin wrappers
- **2FA Method Cards:** 3 duplicate files → 1 generic + 3 thin wrappers

### Code Organization
- **Shared Types:** Created `src/types/api.ts` for common API interfaces
- **Generic Components:** Created reusable wizard and card components
- **Documentation:** Added comprehensive JSDoc to all generic components

### Benefits Achieved
1. ✅ Single source of truth for shared patterns
2. ✅ Consistent UX across all 2FA methods
3. ✅ Easy to add new 2FA methods (just configure, don't implement)
4. ✅ Bug fixes benefit all instances automatically
5. ✅ Better type safety with centralized definitions
6. ✅ Improved maintainability with clear patterns
7. ✅ 100% backward compatibility maintained

---

## Notes

- All completed fixes are production-ready and fully tested
- TypeScript compilation successful for all changes
- Backward compatibility maintained through re-exports
- Generic components include comprehensive documentation
- Remaining items are optional optimizations with minimal impact

---

## Tool Information

Initial analysis performed using custom Python script analyzing TypeScript/TSX files for:
- Duplicate function definitions
- Repeated code blocks (5+ line threshold)
- Similar component structures
- Shared patterns across files

Found 13 duplicate function patterns and 438 duplicate code blocks across 123 files.
