# Invitation Redirect Bug Investigation

## Problem Description

When a new user (User A) accepts an invitation and creates an account, then logs out, the next user (User B) who logs in gets incorrectly redirected to User A's old invitation screen.

## Impact

- Cross-user session contamination
- User B sees invitation details meant for User A
- Potential security/privacy issue
- Poor user experience

---

## Root Cause Analysis

### The Flow That Causes the Bug

1. **User A accepts invitation:**
   - Invitation data stored in `sessionStorage` with key `"circle.invitation.onboarding"`
   - Redirect path stored in `sessionStorage` with key `"circle.invitation.redirect"`
   - Located in: `web/src/features/circles/utils/invitationStorage.ts:78`

2. **User A creates account and logs in:**
   - Login flow reads invitation redirect via `consumeInviteRedirect()` (authHooks.ts:130)
   - Processes invitation finalization
   - The redirect key is removed, but the main invitation data may remain

3. **User A logs out:**
   - Logout calls `authServices.logout()` (authHooks.ts:336-337)
   - Sets access token to null
   - Clears query cache
   - **CRITICAL BUG: Does NOT clear sessionStorage**

4. **User B logs in (same browser tab):**
   - Login flow checks for invitation redirect (authHooks.ts:130)
   - Finds stale invitation data from User A still in sessionStorage
   - Redirects User B to User A's invitation flow

### Why sessionStorage Persists

- `sessionStorage` is tab-scoped and persists until the tab/window closes
- Logging out does NOT automatically clear `sessionStorage`
- The logout function has no cleanup logic for invitation-related storage

---

## Key Files and Logic

### 1. Invitation Storage (`web/src/features/circles/utils/invitationStorage.ts`)

**Storage Keys:**
- `STORAGE_KEY = "circle.invitation.onboarding"` (line 3)
- `REQUEST_KEY_PREFIX = "circle.invitation.request."` (line 4)

**Critical Functions:**
- `saveInvitation(payload)` - Saves to sessionStorage (line 75-97)
- `loadInvitation()` - Reads from sessionStorage (line 99-129)
- `clearInvitation()` - Removes invitation data (line 131-142)
- `markInvitationRequest(token)` - Marks invitation as requested (line 36-46)
- `clearInvitationRequest(token)` - Clears request marker (line 48-58)

**What Gets Stored:**
```typescript
interface StoredCircleInvitation {
    onboardingToken: string;
    expiresInMinutes: number;
    invitation: CircleInvitationDetails;
    sourceToken?: string | null;
    redirectPath?: string | null;
}
```

### 2. Invitation Redirect Storage (`web/src/features/circles/utils/inviteAnalytics.ts`)

**Storage Key:**
- `INVITE_REDIRECT_KEY = "circle.invitation.redirect"` (line 49)

**Critical Functions:**
- `rememberInviteRedirect(path)` - Saves redirect path (line 51-63)
- `consumeInviteRedirect()` - Reads and removes redirect path (line 65-78)

### 3. Logout Flow (`web/src/features/auth/hooks/authHooks.ts`)

**useLogout Hook (lines 331-345):**
```typescript
export function useLogout() {
    const qc = useQueryClient();

    return useMutation({
        mutationFn: async () => {
            await authServices.logout();
            setAccessToken(null);  // ✓ Clears token
            return true;
        },
        onSuccess: () => {
            qc.removeQueries({ queryKey: authKeys.session(), exact: true });
            qc.invalidateQueries({ queryKey: authKeys.session() });
            // ❌ BUG: No sessionStorage cleanup!
        },
    });
}
```

### 4. Login Flow (`web/src/features/auth/hooks/authHooks.ts`)

**useLogin Hook (lines 94-215):**
- Line 130: `consumeInviteRedirect()` - Checks for invitation redirect
- Line 132-135: `finalizeCircleInvitation()` - Processes invitation
  - This function calls `loadInvitation()` which reads from sessionStorage

**Signup Flow (lines 217-329):**
- Similar logic to login
- Line 241: `consumeInviteRedirect()`
- Line 243-246: `finalizeCircleInvitation()`

### 5. Invitation Acceptance Hook (`web/src/features/circles/hooks/useInvitationAcceptance.ts`)

**Key Behavior:**
- Line 70: Initializes state by loading invitation from sessionStorage
- Line 92-107: Subscribes to invitation storage changes
- Line 109-189: Complex effect that loads/processes invitations
- Line 191-214: Auto-finalize effect when user is authenticated
- Line 216-222: Auto-redirect after acceptance

---

## The Fix

### Multi-layered Solution (Defense-in-Depth)

There are **two issues** that need fixing:

#### Issue 1: Decline Flow Doesn't Clear Invitation ❌

**File:** `web/src/features/circles/hooks/useCircleInvitationOnboarding.ts`

The `useRespondToCircleInvitation` hook (lines 102-133) handles both accept and decline actions, but **never clears the invitation storage**.

**Fix:**
```typescript
export function useRespondToCircleInvitation(): UseMutationResult<
    ApiResponseWithMessages<{ invitation: CircleInvitationSummary }>,
    ApiError,
    { invitationId: string; action: "accept" | "decline" }
> {
    const queryClient = useQueryClient();
    const { showAsToast } = useApiMessages();

    return useMutation({
        mutationFn: ({ invitationId, action }) =>
            circleServices.respondToInvitation(invitationId, action),
        onSuccess: (response, variables) => {
            clearInvitation();  // ← ADD THIS
            if (response.messages?.length) {
                showAsToast(response.messages, 200);
            }
            queryClient.invalidateQueries({ queryKey: authKeys.session() });
            queryClient.invalidateQueries({ queryKey: circleKeys.list() });
            queryClient.invalidateQueries({ queryKey: circleKeys.onboarding() });
            trackCircleInviteEvent("invitation_onboarding_responded", {
                invitationId: variables.invitationId,
                action: variables.action,
            });
        },
        onError: (error) => {
            clearInvitation();  // ← ADD THIS
            const status = error.status ?? 400;
            showAsToast(error.messages, status);
            trackCircleInviteEvent("invitation_onboarding_respond_failed", {
                status,
            });
        },
    });
}
```

**Required Import (already exists in this file):**
```typescript
import { clearInvitation } from "../utils/invitationStorage";
```

#### Issue 2: Logout Doesn't Clear Invitation (Safety Net)

**File:** `web/src/features/auth/hooks/authHooks.ts`

Even though accept/decline should clear the invitation, logout should also clear it as a safety measure.

**Fix:**
```typescript
export function useLogout() {
    const qc = useQueryClient();

    return useMutation({
        mutationFn: async () => {
            await authServices.logout();
            setAccessToken(null);

            // Clear invitation-related sessionStorage (safety net)
            clearInvitation();  // Clears "circle.invitation.onboarding"
            rememberInviteRedirect(null);  // Clears "circle.invitation.redirect"

            return true;
        },
        onSuccess: () => {
            qc.removeQueries({ queryKey: authKeys.session(), exact: true });
            qc.invalidateQueries({ queryKey: authKeys.session() });
        },
    });
}
```

**Required Imports:**
```typescript
import { clearInvitation } from "@/features/circles/utils/invitationStorage";
import { rememberInviteRedirect } from "@/features/circles/utils/inviteAnalytics";
```

### Why Both Fixes Are Needed

1. **Primary cleanup** - Clear on accept/decline when the user action completes
2. **Safety net** - Clear on logout to prevent cross-user contamination
3. **Edge cases** - Handles scenarios where user navigates away, network errors, etc.

---

## Testing Checklist

### Reproduction Steps (Before Fix)

#### Scenario 1: Accept then Logout Bug
1. Open browser, navigate to invitation link with `?token=XXX`
2. Create new account (User A)
3. Accept invitation
4. Logout
5. Login with different account (User B)
6. **BUG:** User B gets redirected to User A's invitation screen

#### Scenario 2: Decline Doesn't Clear
1. Open browser, navigate to invitation link with `?token=XXX`
2. Login with existing account
3. Decline invitation
4. Navigate to another invitation link
5. **BUG:** Old invitation data may still be in sessionStorage

### Verification Steps (After Fix)

#### Test 1: Accept Flow Clears Storage
1. Navigate to invitation link with `?token=XXX`
2. Create new account (User A)
3. Accept invitation → Check sessionStorage is cleared
4. Logout → Check sessionStorage is still clear
5. Login with different account (User B)
6. **EXPECTED:** User B goes to home page, no invitation redirect

#### Test 2: Decline Flow Clears Storage
1. Navigate to invitation link with `?token=XXX`
2. Login with existing account
3. Decline invitation → Check sessionStorage is cleared immediately
4. **EXPECTED:** No stale invitation data remains

#### Test 3: Logout Clears Storage (Safety Net)
1. Manually add invitation data to sessionStorage (simulate edge case)
2. Logout
3. Check that sessionStorage is cleared
4. **EXPECTED:** All invitation keys are removed

### Additional Test Cases
- [ ] Accept invitation clears `circle.invitation.onboarding` from sessionStorage
- [ ] Decline invitation clears `circle.invitation.onboarding` from sessionStorage
- [ ] Logout clears `circle.invitation.onboarding` from sessionStorage
- [ ] Logout clears `circle.invitation.redirect` from sessionStorage
- [ ] Accept on error clears invitation storage (already implemented)
- [ ] Decline on error clears invitation storage (needs fix)
- [ ] Login after logout doesn't trigger invitation flow without new invitation
- [ ] Multiple logins/logouts in same tab don't leak invitation data
- [ ] Normal invitation flow still works after the fix
- [ ] Accepting while already logged in clears storage
- [ ] Declining while already logged in clears storage

---

## Related Files

**Frontend (Web):**
- `web/src/features/auth/hooks/authHooks.ts` - **PRIMARY FIX LOCATION**
- `web/src/features/circles/utils/invitationStorage.ts` - Storage utilities
- `web/src/features/circles/utils/inviteAnalytics.ts` - Redirect storage
- `web/src/features/circles/hooks/useInvitationAcceptance.ts` - Invitation logic
- `web/src/features/auth/components/LogoutHandler.tsx` - Logout UI component
- `web/src/route-views/invitations/accept.tsx` - Invitation accept view
- `web/src/routes/invitations.accept.tsx` - Invitation route definition

---

## Notes

- sessionStorage is tab-scoped, so this only affects same-tab logins
- localStorage would cause the issue across all tabs/windows
- The use of sessionStorage is correct; the cleanup is what's missing
- Consider adding a global "clear all user data" utility for logout

---

## Status

- [x] Bug identified
- [x] Root cause analyzed
- [x] Solution designed
- [ ] **Issue 1 Fix:** Add `clearInvitation()` to decline flow (useCircleInvitationOnboarding.ts)
- [ ] **Issue 2 Fix:** Add `clearInvitation()` + `rememberInviteRedirect(null)` to logout (authHooks.ts)
- [ ] Tests written
- [ ] Tests passing
- [ ] Code reviewed
- [ ] Deployed

## Summary

**Root Cause:** Invitation data persists in `sessionStorage` across user sessions because it's not cleared on:
1. ❌ Decline action (primary bug)
2. ❌ Logout (safety net missing)

**Solution:** Clear invitation storage in both places (defense-in-depth)

**Impact:** Medium - Security/privacy issue, cross-user data leakage within same browser tab
