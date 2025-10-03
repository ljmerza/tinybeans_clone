import { api } from "@/modules/login/client";
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
	/**
	 * Initiate OAuth flow
	 * POST /api/auth/google/initiate/
	 */
	initiate: async (
		params: OAuthInitiateRequest,
	): Promise<OAuthInitiateResponse> => {
		return api.post<OAuthInitiateResponse, OAuthInitiateRequest>(
			"/auth/google/initiate/",
			params,
			{ suppressSuccessToast: true },
		);
	},

	/**
	 * Handle OAuth callback
	 * POST /api/auth/google/callback/
	 */
	callback: async (
		params: OAuthCallbackRequest,
	): Promise<OAuthCallbackResponse> => {
		return api.post<OAuthCallbackResponse, OAuthCallbackRequest>(
			"/auth/google/callback/",
			params,
			{ suppressSuccessToast: true },
		);
	},

	/**
	 * Link Google account to authenticated user
	 * POST /api/auth/google/link/
	 */
	link: async (params: OAuthLinkRequest): Promise<OAuthLinkResponse> => {
		return api.post<OAuthLinkResponse, OAuthLinkRequest>(
			"/auth/google/link/",
			params,
		);
	},

	/**
	 * Unlink Google account
	 * DELETE /api/auth/google/unlink/
	 */
	unlink: async (params: OAuthUnlinkRequest): Promise<OAuthUnlinkResponse> => {
		return api.delete<OAuthUnlinkResponse, OAuthUnlinkRequest>(
			"/auth/google/unlink/",
			params,
		);
	},
};
