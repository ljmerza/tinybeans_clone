import { apiClient } from "../api/modernAuthClient";
import type {
	OAuthCallbackRequest,
	OAuthCallbackResponse,
	OAuthInitiateRequest,
	OAuthInitiateResponse,
	OAuthLinkRequest,
	OAuthLinkResponse,
	OAuthUnlinkRequest,
	OAuthUnlinkResponse,
} from "./types";

/**
 * OAuth API Client
 * Handles all Google OAuth API calls
 */
export const oauthApi = {
	/** Initiate OAuth flow - POST /api/auth/google/initiate/ */
	initiate: (params: OAuthInitiateRequest): Promise<OAuthInitiateResponse> =>
		apiClient.post("/auth/google/initiate/", params),

	/** Handle OAuth callback - POST /api/auth/google/callback/ */
	callback: (params: OAuthCallbackRequest): Promise<OAuthCallbackResponse> =>
		apiClient.post("/auth/google/callback/", params),

	/** Link Google account to authenticated user - POST /api/auth/google/link/ */
	link: (params: OAuthLinkRequest): Promise<OAuthLinkResponse> =>
		apiClient.post("/auth/google/link/", params),

	/** Unlink Google account - DELETE /api/auth/google/unlink/ */
	unlink: (params: OAuthUnlinkRequest): Promise<OAuthUnlinkResponse> =>
		apiClient.delete("/auth/google/unlink/", { data: params }),
};
