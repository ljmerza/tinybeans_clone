# Circle Invitation Flow for New Users - Analysis

## Current Flow (BROKEN)

### Step-by-Step

1. **Admin sends invite**
   - Backend: Creates `CircleInvitation` record with `email='newuser@example.com'`
   - Backend: Sends email with invite link: `/invitations/accept?token=abc123`

2. **New user clicks invite link**
   - Frontend: Navigates to `/invitations/accept?token=abc123`
   - Frontend: Calls `POST /circles/invitations/accept/` with token
   - Backend: `CircleInvitationAcceptView.post()` (invitee.py:149)
     - Validates token
     - Creates onboarding token (60min TTL)
     - Stores invitation details in localStorage
   - Frontend: Shows "Accept" button

3. **User clicks "Accept" button**
   - Frontend: Checks if authenticated (line 259)
   - User is NOT authenticated
   - Frontend: Redirects to `/signup?redirect=/invitations/accept?onboarding=xyz789&email=newuser@example.com`

4. **User fills signup form and submits**
   - Frontend: Calls `POST /auth/signup/`
   - Backend: Creates user with `email_verified=False`
   - Backend: Returns signup response: `{..., email_verified: false, ...}`

5. **🔴 PROBLEM: Frontend receives signup response**
   - Frontend: `useSignup` hook (authHooks.ts:233-236)
   - Checks: `if (payload && !payload.email_verified)`
   - **IMMEDIATELY redirects to `/verify-email-required`**
   - **NEVER reaches invitation finalize code** (line 240)

6. **🚫 User stuck on "Verify Email Required" screen**
   - The invitation finalization NEVER happens
   - Email NEVER gets auto-verified
   - User cannot proceed

### The Root Causes

**Frontend Issue 1: useSignup (authHooks.ts:233-236)**
```typescript
if (payload && !payload.email_verified) {
    navigate({ to: "/verify-email-required" });
    return; // ← STOPS HERE, never reaches finalize invitation code below
}

// This code NEVER runs for new users:
const finalizeResult = await finalizeCircleInvitation(showAsToast, ...);
```

**Frontend Issue 2: Root Route Guard (__root.tsx:28-33)**
```typescript
if (!session.user?.email_verified) {
    const isAllowed = allowedPaths.some((path) => pathname.startsWith(path));
    if (!isAllowed) {
        void navigate({ to: "/verify-email-required", replace: true });
    }
}
```
- This catches ALL unverified users globally
- `/invitations/accept` is NOT in allowedPaths
- Even if we fix useSignup, this will still redirect them

## What SHOULD Happen

1. User clicks invite link → stores onboarding token
2. User signs up → gets `email_verified=false` from backend
3. **Frontend checks for pending invitation onboarding token**
4. **If invitation exists, skip email verification redirect**
5. **Call finalize invitation endpoint**
6. **Backend auto-verifies email during finalization**
7. **Redirect to circle page**

## Backend Status

✅ **Backend is FIXED** (already done):
- `CircleInvitationFinalizeView` no longer requires `IsEmailVerified` permission
- Auto-verifies email during finalization (invitee.py:286-289)
- Tests pass

## Frontend Fixes Applied ✅

### Fix 1: Update useSignup Hook (authHooks.ts:240-257)
Check for invitation redirect BEFORE redirecting to verify-email:

```typescript
// After signup, check if we have an invitation to finalize
const redirectTarget = options?.redirect ?? consumeInviteRedirect();
const invitationRedirect = parseInvitationRedirect(redirectTarget);

// If we have an invitation, finalize it first (which will auto-verify email)
const finalizeResult = await finalizeCircleInvitation(
    showAsToast,
    invitationRedirect?.onboardingToken,
);

// Refresh session after finalization (email may have been auto-verified)
if (finalizeResult.status === "success") {
    await qc.invalidateQueries({ queryKey: authKeys.session() });
}

// ONLY redirect to verify-email if NO invitation
if (payload && !payload.email_verified && !invitationRedirect) {
    navigate({ to: "/verify-email-required" });
    return;
}
```

### Fix 2: Update useLogin Hook (authHooks.ts:129-146)
Same fix as useSignup - finalize invitation first, refresh session, then check email verification.

### Fix 3: Update Root Route Guard (__root.tsx:22-42)
Add `/invitations/accept` to allowed paths AND check for pending invitations:

```typescript
const allowedPaths = [
    "/verify-email",
    "/verify-email-required",
    "/logout",
    "/auth/google-callback",
    "/invitations/accept", // ← ADDED
];

if (!session.user?.email_verified) {
    // Don't redirect if there's a pending invitation (email will be auto-verified during finalization)
    const pendingInvitation = loadInvitation();
    if (pendingInvitation) {
        return; // ← PREVENTS FLASH OF VERIFY SCREEN
    }

    const isAllowed = allowedPaths.some((path) => pathname.startsWith(path));
    if (!isAllowed) {
        void navigate({ to: "/verify-email-required", replace: true });
    }
    return;
}
```

**This prevents the flash of the verify email screen during invitation finalization.**

### Fix 4: Session Refresh (authHooks.ts:138-140, 249-251)
**CRITICAL FIX:** After successful finalization, invalidate session query to get updated `email_verified` status:

```typescript
if (finalizeResult.status === "success") {
    await qc.invalidateQueries({ queryKey: authKeys.session() });
}
```

This ensures the frontend session reflects the backend's auto-verified email status.

## Security Validation

✅ **This is secure because:**
- Onboarding token is one-time use (consumed on finalize)
- Token has 60-minute TTL
- Email match validation prevents account takeover (invitee.py:274-282)
- User proved email ownership by clicking link from their inbox
- Same security model as Slack, Discord, GitHub

## Testing Checklist

After fixes:
- [x] New user clicks invite → signs up → auto-verified → joins circle → **NO VERIFY SCREEN**
- [x] Existing verified user clicks invite → logs in → joins circle
- [ ] Existing unverified user clicks invite → logs in → still blocked (security)
- [ ] Invalid token → shows error
- [ ] Expired token → shows expired message
- [x] User without invite → normal email verification flow works

## Summary of All Fixes

**Backend (2 changes):**
1. Removed `IsEmailVerified` permission from `CircleInvitationFinalizeView` (invitee.py:236)
2. Auto-verify email during finalization (invitee.py:286-289)

**Frontend (5 changes):**
1. Add `/invitations/accept` to allowed paths (__root.tsx:27)
2. Check for pending invitation before redirecting to verify screen (__root.tsx:31-35) **← Prevents flash**
3. Reorder `useLogin` to finalize BEFORE email check (authHooks.ts:129-146)
4. Reorder `useSignup` to finalize BEFORE email check (authHooks.ts:240-257)
5. Refresh session after finalization (authHooks.ts:138-140, 249-251)
