# Code Duplication Report - Web Project

**Generated:** $(date)  
**Scope:** `/web/src` directory

## Executive Summary

This report identifies duplicated code patterns in the web project that could be refactored to improve maintainability and reduce code redundancy. The analysis found several categories of duplication ranging from near-identical components to repeated code patterns.

---

## Critical Duplications (High Priority)

### 1. **Confirm Dialog Components** ⚠️ HIGH PRIORITY

**Location:**
- `src/components/ui/confirm-dialog.tsx` (152 lines)
- `src/components/ui/confirm-dialog-with-content.tsx` (162 lines)

**Issue:** These two components share ~95% identical code. The only difference is that `confirm-dialog-with-content.tsx` has a `children` prop and renders it in a div with `py-4` class.

**Duplication Details:**
- Identical handler functions: `handleConfirm`, `handleCancel`, `handleOpenChange`
- Identical props interface (except `children` in one)
- Identical JSX structure (except one line)
- Identical styling logic

**Recommended Fix:**
Consolidate into a single component with an optional `children` prop. The simpler `ConfirmDialog` can be a wrapper or the same component can handle both cases.

```typescript
// Proposed unified component
export function ConfirmDialog({
  children,
  // ... other props
}: ConfirmDialogProps) {
  // ... handlers (same as current)
  
  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          {description && <DialogDescription>{description}</DialogDescription>}
        </DialogHeader>
        {children && <div className="py-4">{children}</div>}
        <DialogFooter>
          {/* buttons */}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

**Estimated LOC Reduction:** ~150 lines

---

### 2. **App.tsx vs Layout.tsx Header Duplication** ⚠️ HIGH PRIORITY

**Location:**
- `src/App.tsx` (lines 10-38)
- `src/components/Layout.tsx` (lines 47-67)

**Issue:** Near-identical header navigation structure duplicated between the two files.

**Duplication Details:**
```tsx
// Both files have nearly identical structure:
<header className="bg-white shadow-sm">
  <div className="container-page">
    <div className="flex justify-between items-center h-16">
      <div className="flex items-center">
        <Link to="/" className="text-xl font-bold text-gray-900 hover:text-gray-700">
          Home
        </Link>
      </div>
      <nav className="flex items-center gap-4">
        {/* auth-dependent links */}
      </nav>
    </div>
  </div>
</header>
```

**Recommended Fix:**
- Remove `App.tsx` entirely if possible and use the `Layout` component consistently
- OR extract header into a separate `<Header />` component used by both

**Estimated LOC Reduction:** ~30 lines

---

### 3. **QueryClient Configuration Duplication**

**Location:**
- `src/main.tsx` (lines 12-18)
- `src/integrations/tanstack-query/root-provider.tsx` (lines 10-17)

**Issue:** Identical QueryClient configuration in two places.

**Duplication:**
```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: false,
    },
  },
});
```

**Recommended Fix:**
Create a shared factory function:

```typescript
// src/lib/queryClient.ts
export function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 1000 * 60 * 5,
        retry: false,
      },
    },
  });
}
```

**Estimated LOC Reduction:** ~10 lines (with improved maintainability)

---

## Moderate Duplications

### 4. **Login Card Components** 🔶 MEDIUM PRIORITY

**Location:**
- `src/features/auth/components/LoginCard.tsx`
- `src/features/auth/components/ModernLoginCard.tsx`

**Issue:** These components are nearly identical (>90% code similarity). Both have:
- Identical form structure
- Identical validation logic
- Identical error handling pattern
- Identical UI layout (Google OAuth button, divider, form fields)
- Same footer links

**Duplication Details:**
```typescript
// Both have identical error handling:
catch (error: any) {
  console.error("Login submission error:", error);
  const generalErrors = getGeneral(error.messages);
  if (generalErrors.length > 0) {
    setGeneralError(generalErrors.join(". "));
  } else {
    setGeneralError(error.message ?? "Login failed");
  }
}
```

**Note:** According to comments in `ModernLoginCard.tsx`, this is intentionally separate as a demonstration of ADR-012 notification strategy. However, the implementation is identical.

**Recommended Fix:**
- If both approaches are truly the same, consolidate into one component
- If there are intentional differences, document them clearly and extract shared logic

**Estimated LOC Reduction:** ~150 lines if consolidated

---

### 5. **2FA Setup Wizard Steps** 🔶 MEDIUM PRIORITY

This is actually a larger pattern affecting **NINE** components across three 2FA methods (Email, SMS, TOTP).

#### 5a. Intro Steps

**Location:**
- `src/features/twofa/components/setup/email/EmailIntroStep.tsx` (51 lines)
- `src/features/twofa/components/setup/sms/SmsIntroStep.tsx` (71 lines)
- `src/features/twofa/components/setup/totp/TotpIntroStep.tsx` (54 lines)

**Issue:** Nearly identical structure with only content variations.

#### 5b. Verify Steps

**Location:**
- `src/features/twofa/components/setup/email/EmailVerifyStep.tsx`
- `src/features/twofa/components/setup/sms/SmsVerifyStep.tsx`
- `src/features/twofa/components/setup/totp/TotpVerifyStep.tsx`

**Issue:** 
- Email and SMS verify steps are **virtually identical** (same props, same structure)
- TOTP verify step is similar but slightly different (no resend functionality)
- All three share the same verification input handling and validation

**Common Pattern:**
```tsx
<WizardSection title="..." description="...">
  <VerificationInput
    value={code}
    onChange={onCodeChange}
    onComplete={onVerify}
    disabled={isVerifying}
  />
  {errorMessage && <StatusMessage variant="error">{errorMessage}</StatusMessage>}
</WizardSection>
<WizardFooter>
  {/* Buttons with different configurations */}
</WizardFooter>
```

#### 5c. Recovery Steps

**Location:**
- `src/features/twofa/components/setup/email/EmailRecoveryStep.tsx` (32 lines)
- `src/features/twofa/components/setup/sms/SmsRecoveryStep.tsx` (32 lines)
- `src/features/twofa/components/setup/totp/TotpRecoveryStep.tsx` (40 lines)

**Issue:** Nearly 100% identical except for title/description text:

```tsx
<WizardSection title="✅ [Method] 2FA Enabled" description="...">
  {recoveryCodes && <RecoveryCodeList codes={recoveryCodes} showDownloadButton />}
  {/* TOTP has an extra InfoPanel */}
</WizardSection>
<WizardFooter>
  <Button onClick={onComplete}>Done</Button>
</WizardFooter>
```

**Recommended Fix:**

Create generic wizard step components with configuration objects:

```typescript
// Generic components
export function IntroStep({ config, state, handlers }: IntroStepProps) {
  // Configurable intro step
}

export function VerifyStep({ config, state, handlers }: VerifyStepProps) {
  // Configurable verify step
}

export function RecoveryStep({ config, state, handlers }: RecoveryStepProps) {
  // Configurable recovery step
}

// Configuration per method
const EMAIL_CONFIG = {
  intro: { title: "Verify by Email", /* ... */ },
  verify: { /* ... */ },
  recovery: { title: "✅ Email 2FA Enabled", /* ... */ },
};
```

**Estimated LOC Reduction:** ~250 lines (from 9 files to 3 generic + 3 config files)

---

### 6. **2FA Method Card Components** 🔶 MEDIUM PRIORITY

**Location:**
- `src/features/twofa/components/methods/EmailMethodCard.tsx` (99 lines)
- `src/features/twofa/components/methods/SmsMethodCard.tsx` (101 lines)
- `src/features/twofa/components/methods/TotpMethodCard.tsx` (94 lines)

**Issue:** Three nearly identical card components with only content variations.

**Common Structure:**
```tsx
<Card className="border-2 border-gray-200">
  <CardHeader className="flex items-start gap-4 pb-0">
    <div className="text-3xl">{icon}</div>
    <div className="flex-1 space-y-2">
      <CardTitle>{title}</CardTitle>
      <CardDescription>{description}</CardDescription>
      <ChipGroup>
        {/* Different chips per method */}
      </ChipGroup>
      {isCurrent && <StatusMessage variant="success">Current default</StatusMessage>}
      {/* SMS has extra phone number display */}
    </div>
  </CardHeader>
  <CardContent className="pt-4">
    {configured ? (
      <ButtonGroup>
        {/* Similar button patterns */}
      </ButtonGroup>
    ) : (
      <Button onClick={onSetup}>Set Up</Button>
    )}
  </CardContent>
</Card>
```

**Differences:**
- Icon emoji (📧, 💬, 📱)
- Title and description text
- Chip badges (different features)
- SMS has phone number display
- Email has conditional removal button vs. always showing it

**Recommended Fix:**

Create a generic `TwoFactorMethodCard` component:

```typescript
interface MethodCardConfig {
  icon: string;
  title: string;
  description: string;
  chips: Array<{ label: string; variant: ChipVariant }>;
  additionalInfo?: React.ReactNode;
}

export function TwoFactorMethodCard({
  config,
  isCurrent,
  configured,
  // ... handlers
}: Props) {
  // Render with config
}

// Usage:
const EMAIL_CONFIG: MethodCardConfig = {
  icon: "📧",
  title: "Email Verification",
  description: "Receive verification codes via email.",
  chips: [
    { label: "Simple", variant: "primary" },
    { label: "No Extra App Needed", variant: "info" }
  ],
};
```

**Estimated LOC Reduction:** ~200 lines (consolidate 3 files into 1 generic + configs)

---

### 7. **API Response Interface Duplication**

**Location:**
- `src/i18n/notificationUtils.ts` (lines 20-24)
- `src/lib/httpClient.ts` (lines 23-26)

**Issue:** Identical `ApiResponse<T>` interface defined in two places.

**Duplication:**
```typescript
export interface ApiResponse<T = unknown> {
  data?: T;
  messages?: ApiMessage[];
  error?: string;
}
```

**Recommended Fix:**
Move to a shared types file:

```typescript
// src/types/api.ts
export interface ApiResponse<T = unknown> {
  data?: T;
  messages?: ApiMessage[];
  error?: string;
}
```

**Estimated LOC Reduction:** ~5 lines (plus improved type safety)

---

## Minor Duplications (Low Priority)

### 7. **Error Handling Patterns** 🔷 LOW PRIORITY

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

---

### 8. **2FA Navigation State** 🔷 LOW PRIORITY

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

---

### 9. **Message Display Pattern** 🔷 LOW PRIORITY

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

---

### 10. **Card Component Imports** 🔷 LOW PRIORITY

**Location:**
- `src/components/Wizard.tsx`
- `src/components/AuthCard.tsx`

**Issue:** Identical Card component imports:
```typescript
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "./ui/card";
```

**Note:** This is more of a pattern than true duplication - imports are necessary.

---

## Summary Statistics

| Priority | Category | Count | Est. LOC Reduction |
|----------|----------|-------|-------------------|
| HIGH | Component Duplication | 3 | ~190 lines |
| MEDIUM | Similar Components | 3 | ~600 lines |
| LOW | Code Patterns | 4 | ~50 lines |
| **TOTAL** | | **10** | **~840 lines** |

**Note:** The Medium priority items include:
- 2FA Setup Wizard (9 component files → 3-6 files): ~250 lines
- 2FA Method Cards (3 files → 1 file + configs): ~200 lines  
- Login Card variations: ~150 lines

---

## Recommendations

### Immediate Actions (High Priority)

1. **Consolidate Confirm Dialog Components** - Merge the two confirm dialog components into one flexible component. This is the most significant duplication.

2. **Unify Header Components** - Decide whether to keep `App.tsx` or use `Layout` consistently throughout the application.

3. **Centralize QueryClient Configuration** - Extract to shared factory function.

### Medium-Term Actions (Medium Priority)

4. **Review Login Card Components** - Determine if both are needed or if they can be consolidated given they have identical implementations.

5. **Refactor 2FA Setup Wizard Steps** - Create generic wizard step components (Intro, Verify, Recovery) to replace the 9 duplicate files across Email/SMS/TOTP methods. This is the largest source of duplication (~250 LOC reduction).

6. **Refactor 2FA Method Cards** - Consolidate the three method card components (Email, SMS, TOTP) into a single generic card component with configuration objects (~200 LOC reduction).

7. **Centralize API Types** - Move shared interfaces like `ApiResponse` to a common types file.

### Long-Term Actions (Low Priority)

7. **Extract Error Handling Utilities** - Create reusable error handling functions for common patterns.

8. **Review Navigation Patterns** - Consider extracting 2FA navigation logic.

9. **Audit Message Display** - Review if toast message display should be centralized.

---

## Notes

- This analysis found **13 duplicate function patterns** and **438 duplicate code blocks** (5+ lines)
- Many block duplications are legitimate (imports, standard patterns)
- Focus on component-level duplications for maximum impact
- Consider code reusability vs. readability tradeoffs

---

## Tool Information

Analysis performed using custom Python script analyzing TypeScript/TSX files for:
- Duplicate function definitions
- Repeated code blocks (5+ line threshold)
- Similar component structures
- Shared patterns across files

