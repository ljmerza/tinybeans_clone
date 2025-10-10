/**
 * Two-Factor Authentication Navigation Utilities
 *
 * Provides consistent 2FA redirect handling across authentication flows.
 */

import type { TwoFactorMethod } from "@/features/twofa";
import type { TwoFactorNavigateState } from "../types";

/**
 * Extracts the 2FA navigation state from an authentication response.
 *
 * Callers can use the returned state to navigate to the verification route.
 *
 * @param data - Login/signup response data
 * @returns redirect state when 2FA is required, otherwise null
 *
 * @example
 * ```typescript
 * const redirectState = handleTwoFactorRedirect(data);
 * if (redirectState) {
 *   navigate({ to: "/profile/2fa/verify", state: redirectState });
 *   return;
 * }
 * ```
 */
export function handleTwoFactorRedirect(data: {
	requires_2fa?: boolean;
	partial_token?: string;
	method?: TwoFactorMethod;
	message?: string;
}): TwoFactorNavigateState | null {
	if (data.requires_2fa && data.partial_token && data.method) {
		return {
			partialToken: data.partial_token,
			method: data.method,
			message: data.message,
		};
	}
	return null;
}
