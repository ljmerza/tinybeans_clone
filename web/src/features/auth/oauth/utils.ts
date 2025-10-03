import type {
	OAuthError,
	OAuthErrorCode,
	OAuthErrorInfo,
} from "./types";

/**
 * OAuth Error Messages
 * User-friendly error messages for all OAuth error codes from ADR-010
 */
export const OAUTH_ERROR_MESSAGES: Record<OAuthErrorCode, OAuthErrorInfo> = {
	UNVERIFIED_ACCOUNT_EXISTS: {
		title: "Email Verification Required",
		message:
			"An account with this email exists but is not verified. Please check your email for the verification link.",
		action: "Resend Verification Email",
		severity: "warning",
	},
	GOOGLE_API_ERROR: {
		title: "Connection Error",
		message:
			"Unable to connect to Google. Please try again in a moment.",
		action: "Retry",
		severity: "error",
	},
	INVALID_STATE_TOKEN: {
		title: "Session Expired",
		message: "Your sign-in session has expired. Please try again.",
		action: "Try Again",
		severity: "info",
	},
	RATE_LIMIT_EXCEEDED: {
		title: "Too Many Attempts",
		message:
			"You've tried too many times. Please wait 15 minutes before trying again.",
		action: null,
		severity: "error",
	},
	GOOGLE_ACCOUNT_ALREADY_LINKED: {
		title: "Already Linked",
		message: "This Google account is already linked to another user.",
		action: "Contact Support",
		severity: "error",
	},
	INVALID_REDIRECT_URI: {
		title: "Configuration Error",
		message:
			"There was a problem with the sign-in configuration. Please contact support.",
		action: "Contact Support",
		severity: "error",
	},
	CANNOT_UNLINK_WITHOUT_PASSWORD: {
		title: "Password Required",
		message:
			"You cannot unlink your Google account without setting a password first.",
		action: "Set Password",
		severity: "error",
	},
	INVALID_PASSWORD: {
		title: "Incorrect Password",
		message: "The password you entered is incorrect. Please try again.",
		action: "Try Again",
		severity: "error",
	},
	UNKNOWN_ERROR: {
		title: "Sign-in Failed",
		message: "An unexpected error occurred. Please try again.",
		action: "Try Again",
		severity: "error",
	},
};

/**
 * Get user-friendly error message from OAuth error
 */
export function getOAuthErrorMessage(
	error: unknown,
): OAuthErrorInfo {
	// Check if it's an OAuth error response
	if (error && typeof error === "object" && "data" in error) {
		const data = (error as { data: unknown }).data;
		if (data && typeof data === "object" && "error" in data) {
			const oauthError = data as OAuthError;
			const errorCode = oauthError.error?.code as OAuthErrorCode;
			const errorInfo = OAUTH_ERROR_MESSAGES[errorCode];
			if (errorInfo) {
				return errorInfo;
			}
		}
	}

	// Fallback to unknown error
	return OAUTH_ERROR_MESSAGES.UNKNOWN_ERROR;
}

/**
 * Validate OAuth state token matches stored state
 */
export function validateOAuthState(
	receivedState: string,
	storedState: string | null,
): boolean {
	if (!storedState) {
		console.error("No stored OAuth state found");
		return false;
	}
	if (receivedState !== storedState) {
		console.error("OAuth state mismatch");
		return false;
	}
	return true;
}

/**
 * Store OAuth state in sessionStorage
 */
export function storeOAuthState(state: string): void {
	sessionStorage.setItem("oauth_state", state);
}

/**
 * Retrieve OAuth state from sessionStorage
 */
export function getOAuthState(): string | null {
	return sessionStorage.getItem("oauth_state");
}

/**
 * Clear OAuth state from sessionStorage
 */
export function clearOAuthState(): void {
	sessionStorage.removeItem("oauth_state");
}

/**
 * Get current redirect URI for OAuth
 */
export function getRedirectUri(): string {
	return `${window.location.origin}/auth/google/callback`;
}
