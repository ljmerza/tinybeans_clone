/**
 * CSRF Token Utilities
 * Ensures CSRF token is available before making authenticated requests
 */

import { API_BASE } from "@/features/auth";

let csrfInitialized = false;
let csrfInitPromise: Promise<void> | null = null;

/**
 * Initialize CSRF token by fetching from backend
 * This ensures the csrftoken cookie is set
 */
export async function ensureCsrfToken(): Promise<void> {
	if (csrfInitialized) return;
	if (csrfInitPromise) return csrfInitPromise;

	csrfInitPromise = (async () => {
		try {
			await fetch(`${API_BASE}/auth/csrf/`, {
				method: "GET",
				credentials: "include",
			});
			csrfInitialized = true;
		} catch (error) {
			console.error("Failed to initialize CSRF token:", error);
			// Don't throw - let the actual API call fail with proper error
		} finally {
			csrfInitPromise = null;
		}
	})();

	return csrfInitPromise;
}

/**
 * Reset CSRF initialization state
 * Useful for testing or after logout
 */
export function resetCsrfState(): void {
	csrfInitialized = false;
	csrfInitPromise = null;
}
