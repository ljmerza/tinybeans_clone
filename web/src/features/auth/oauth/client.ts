import { apiClient } from "../api/authClient";
import type {
	ApiMessage,
	OAuthCallbackRequest,
	OAuthCallbackResponse,
	OAuthInitiateRequest,
	OAuthInitiateResponse,
	OAuthLinkRequest,
	OAuthLinkResponse,
	OAuthUnlinkRequest,
	OAuthUnlinkResponse,
} from "./types";

type Envelope<T> = { data?: T; messages?: ApiMessage[] };

/**
 * The backend wraps success bodies as `{ data, messages }` (success_response).
 * Flatten them so callers read `google_oauth_url`, `tokens`, `user` directly,
 * keeping any top-level messages.
 */
export function unwrapOAuthResponse<T extends { messages?: ApiMessage[] }>(
	response: Envelope<T> | T,
): T {
	const envelope = response as Envelope<T>;
	if (envelope && typeof envelope === "object" && envelope.data !== undefined) {
		return {
			...envelope.data,
			messages: envelope.messages ?? envelope.data.messages,
		} as T;
	}
	return response as T;
}

/**
 * OAuth API Client
 * Handles all Google OAuth API calls
 */
export const oauthApi = {
	/** Initiate OAuth flow - POST /api/auth/google/initiate/ */
	initiate: (params: OAuthInitiateRequest): Promise<OAuthInitiateResponse> =>
		apiClient
			.post<Envelope<OAuthInitiateResponse>>("/auth/google/initiate/", params)
			.then(unwrapOAuthResponse),

	/** Handle OAuth callback - POST /api/auth/google/callback/ */
	callback: (params: OAuthCallbackRequest): Promise<OAuthCallbackResponse> =>
		apiClient
			.post<Envelope<OAuthCallbackResponse>>("/auth/google/callback/", params)
			.then(unwrapOAuthResponse),

	/** Link Google account to authenticated user - POST /api/auth/google/link/ */
	link: (params: OAuthLinkRequest): Promise<OAuthLinkResponse> =>
		apiClient
			.post<Envelope<OAuthLinkResponse>>("/auth/google/link/", params)
			.then(unwrapOAuthResponse),

	/** Unlink Google account - DELETE /api/auth/google/unlink/ */
	unlink: (params: OAuthUnlinkRequest): Promise<OAuthUnlinkResponse> =>
		apiClient
			.delete<Envelope<OAuthUnlinkResponse>>("/auth/google/unlink/", params)
			.then(unwrapOAuthResponse),
};
