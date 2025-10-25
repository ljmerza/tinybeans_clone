/**
 * Authentication HTTP Client
 *
 * Provides HTTP client for authentication operations with:
 * - Automatic token management
 * - Token refresh on 401 errors
 * - CSRF protection
 */
import i18next from "@/i18n/config";
import { API_BASE, createHttpClient } from "@/lib/httpClient";
import type { RequestOptions } from "@/lib/httpClient";
import { showToast } from "@/lib/toast";
import { router } from "@/router";
import { authStore } from "../store/authStore";
import { refreshAccessToken } from "../utils/refreshToken";

export { refreshAccessToken };

/**
 * HTTP client for authentication operations
 * Components handle messages explicitly for context-aware presentation
 */
function handleEmailVerificationRedirect(data: unknown) {
	if (!data || typeof data !== "object") {
		return false;
	}
	const payload = data as Record<string, unknown>;
	if (payload.error !== "email_verification_required") {
		return false;
	}
	const redirectPath =
		typeof payload.redirect_to === "string"
			? (payload.redirect_to as string)
			: "/verify-email-required";
	if (typeof window !== "undefined") {
		const currentPath = window.location.pathname;
		if (currentPath === redirectPath) {
			return true;
		}
		const message = i18next.t("auth.email_verification.redirect_message");
		showToast({
			message,
			level: "info",
			id: "email-verification-required",
		});
		if (redirectPath === "/verify-email-required") {
			void router
				.navigate({ to: "/verify-email-required", replace: true })
				.catch(() => {
					window.location.assign(redirectPath);
				});
		} else {
			window.location.assign(redirectPath);
		}
	}
	return true;
}

export const apiClient = createHttpClient({
	getAuthToken: () => authStore.state.accessToken,
	onUnauthorized: refreshAccessToken,
	onError: (data) => {
		if (handleEmailVerificationRedirect(data)) {
			return;
		}
	},
	skipRetryPaths: ["/auth/login/", "/auth/signup/", "/auth/token/refresh/"],
});

export { API_BASE };
export type { RequestOptions };
