/**
 * Two-Factor Authentication Navigation Utilities
 * 
 * Provides consistent 2FA redirect handling across authentication flows.
 */

import type { TwoFactorNavigateState } from "../types";

/**
 * Handles 2FA redirect after login/signup when 2FA is required
 * 
 * Extracts 2FA state from response and navigates to verification page
 * 
 * @param data - Login/signup response data
 * @param navigate - TanStack Router navigate function
 * @returns true if 2FA redirect was triggered, false otherwise
 * 
 * @example
 * ```typescript
 * onSuccess: ({ data }) => {
 *   if (handleTwoFactorRedirect(data, navigate)) {
 *     return; // 2FA required, stop processing
 *   }
 *   // Continue with normal login flow
 * }
 * ```
 */
export function handleTwoFactorRedirect(
	data: {
		requires_2fa?: boolean;
		partial_token?: string;
		method?: string;
		message?: string;
	},
	navigate: (options: any) => any
): boolean {
	if (data.requires_2fa && data.partial_token && data.method) {
		const state: TwoFactorNavigateState = {
			partialToken: data.partial_token,
			method: data.method as any,
			message: data.message,
		};
		navigate({ to: "/2fa/verify", state: state as never });
		return true;
	}
	return false;
}
