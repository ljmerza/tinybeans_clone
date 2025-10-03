import { API_BASE, createHttpClient, getCsrfToken } from "@/lib/httpClient";
import type { RequestOptions } from "@/lib/httpClient";
import { showApiToast } from "@/lib/toast";
import { authStore, setAccessToken } from "../store/authStore";
import type { RefreshAccessTokenResponse } from "../types";

export async function refreshAccessToken(): Promise<boolean> {
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
	if (data?.access) {
		setAccessToken(data.access);
		return true;
	}
	// Clear token if response doesn't contain access token
	setAccessToken(null);
	return false;
}

// Create auth-specific HTTP client with integrated auth logic
export const api = createHttpClient({
	getAuthToken: () => authStore.state.accessToken,
	onUnauthorized: refreshAccessToken,
	onSuccess: showApiToast,
	onError: (data, status, fallbackMessage) =>
		showApiToast(data, status, { fallbackMessage }),
	skipRetryPaths: ["/auth/login/", "/auth/signup/", "/auth/token/refresh/"],
});

export { API_BASE };
export type { RequestOptions };
