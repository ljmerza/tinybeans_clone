import { API_BASE, createHttpClient } from "@/lib/httpClient";
import type { RequestOptions } from "@/lib/httpClient";
import { showApiToast } from "@/lib/toast";
import { authStore } from "../store/authStore";
import { refreshAccessToken } from "../utils/refreshToken";

export { refreshAccessToken };

// Create auth-specific HTTP client with integrated auth logic
// NOTE: onSuccess and onError callbacks are deprecated per ADR-012.
// Components should explicitly handle messages using i18n translation.
// These are kept temporarily for backward compatibility during migration.
export const api = createHttpClient({
	getAuthToken: () => authStore.state.accessToken,
	onUnauthorized: refreshAccessToken,
	// TODO: Remove these callbacks after migrating all components to handle messages explicitly
	onSuccess: showApiToast,
	onError: (data, status, fallbackMessage) =>
		showApiToast(data, status, { fallbackMessage }),
	skipRetryPaths: ["/auth/login/", "/auth/signup/", "/auth/token/refresh/"],
});

export { API_BASE };
export type { RequestOptions };
