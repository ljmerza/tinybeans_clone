import { apiClient as authApi } from "@/features/auth/api/authClient";

/**
 * Emails the signed-in user a one-time re-authentication code (202, no body).
 * A new request replaces the previous code; sensitive actions, such as
 * creating an API token, take the code in their own request.
 */
export function sendReauthCode() {
	return authApi.post<Record<string, never>>("/auth/reauth/code/", {});
}
