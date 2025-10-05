/**
 * Shared refresh token utility
 * Prevents concurrent refresh token calls by deduplicating requests
 */

import { API_BASE, getCsrfToken } from "@/lib/httpClient";
import { setAccessToken } from "../store/authStore";
import type { RefreshAccessTokenResponse } from "../types";

// Track in-flight refresh requests to prevent concurrent calls
let refreshPromise: Promise<boolean> | null = null;

/**
 * Refresh the access token using the refresh token cookie
 * Deduplicates concurrent calls to prevent multiple simultaneous refresh requests
 */
export async function refreshAccessToken(): Promise<boolean> {
	// If there's already a refresh in progress, return that promise
	if (refreshPromise) {
		return refreshPromise;
	}

	// Create new refresh promise
	refreshPromise = (async () => {
		try {
			const csrfToken = getCsrfToken();
			const headers: HeadersInit = { "Content-Type": "application/json" };
			if (csrfToken) headers["X-CSRFToken"] = csrfToken;

			const res = await fetch(`${API_BASE}/auth/token/refresh/`, {
				method: "POST",
				credentials: "include",
				headers,
			});
			
			if (!res.ok) {
				// Clear the access token when refresh fails to log out the user
				setAccessToken(null);
				return false;
			}
			
			const data: RefreshAccessTokenResponse | null = await res
				.json()
				.catch(() => null);

			// Backend wraps response in { data: { access: "..." } }
			const tokenData = (data as any)?.data || data;
			
			if (tokenData?.access) {
				setAccessToken(tokenData.access);
				return true;
			}
			
			// Clear token if response doesn't contain access token
			setAccessToken(null);
			return false;
		} finally {
			// Clear the promise after completion so future calls can proceed
			refreshPromise = null;
		}
	})();

	return refreshPromise;
}
