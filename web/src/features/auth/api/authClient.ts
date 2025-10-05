/**
 * Authentication HTTP Client
 * 
 * Provides HTTP client for authentication operations with:
 * - Automatic token management
 * - Token refresh on 401 errors
 * - CSRF protection
 */
import { API_BASE, createHttpClient } from "@/lib/httpClient";
import type { RequestOptions } from "@/lib/httpClient";
import { authStore } from "../store/authStore";
import { refreshAccessToken } from "../utils/refreshToken";

export { refreshAccessToken };

/**
 * HTTP client for authentication operations
 * Components handle messages explicitly for context-aware presentation
 */
export const apiClient = createHttpClient({
	getAuthToken: () => authStore.state.accessToken,
	onUnauthorized: refreshAccessToken,
	// No onSuccess/onError - components handle messages
	skipRetryPaths: ["/auth/login/", "/auth/signup/", "/auth/token/refresh/"],
});

export { API_BASE };
export type { RequestOptions };
