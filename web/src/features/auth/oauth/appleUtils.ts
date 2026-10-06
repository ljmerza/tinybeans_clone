const APPLE_STATE_KEY = "apple_oauth_state";

/**
 * SPA page the API forwards Apple's response to.
 * Must match routes/auth/apple-callback.tsx and the backend
 * APPLE_OAUTH_ALLOWED_RETURN_URIS.
 */
export function getAppleRedirectUri(): string {
	return `${window.location.origin}/auth/apple-callback`;
}

export function storeAppleOAuthState(state: string): void {
	sessionStorage.setItem(APPLE_STATE_KEY, state);
}

export function getAppleOAuthState(): string | null {
	return sessionStorage.getItem(APPLE_STATE_KEY);
}

export function clearAppleOAuthState(): void {
	sessionStorage.removeItem(APPLE_STATE_KEY);
}

export interface AppleCallbackParams {
	code?: string;
	state?: string;
	error?: string;
}

/**
 * The API puts Apple's result in the URL fragment (`#code=…&state=…` or
 * `#error=…`) so the one-time code never reaches server logs.
 */
export function parseAppleCallbackFragment(hash: string): AppleCallbackParams {
	const params = new URLSearchParams(hash.replace(/^#/, ""));
	return {
		code: params.get("code") ?? undefined,
		state: params.get("state") ?? undefined,
		error: params.get("error") ?? undefined,
	};
}
