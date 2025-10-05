/**
 * Modern HTTP Client (ADR-012 Compliant)
 * 
 * This client follows ADR-012: Notification Strategy
 * - No automatic toasts
 * - Components explicitly handle messages
 * - Supports i18n message format
 * 
 * Use this for new code. The old authClient.ts is kept for backward compatibility.
 */
import { API_BASE, createHttpClient } from "@/lib/httpClient";
import type { RequestOptions } from "@/lib/httpClient";
import { authStore } from "../store/authStore";
import { refreshAccessToken } from "../utils/refreshToken";

export { refreshAccessToken };

/**
 * Modern HTTP client following ADR-012
 * No automatic toasts - components handle messages explicitly
 */
export const apiClient = createHttpClient({
	getAuthToken: () => authStore.state.accessToken,
	onUnauthorized: refreshAccessToken,
	// No onSuccess/onError - components handle messages
	skipRetryPaths: ["/auth/login/", "/auth/signup/", "/auth/token/refresh/"],
});

export { API_BASE };
export type { RequestOptions };
