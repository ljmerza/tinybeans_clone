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
 * Uses modernAuthClient with ADR-012 notification system
 */
export const oauthApi = {
	/**
	 * Initiate OAuth flow
	 * POST /api/auth/google/initiate/
	 */
	initiate: async (
		params: OAuthInitiateRequest,
	): Promise<OAuthInitiateResponse> => {
		const response = await apiClient.post<OAuthInitiateResponse>(
			"/auth/google/initiate/",
			params,
		);
		return response.data;
	},

	/**
	 * Handle OAuth callback
	 * POST /api/auth/google/callback/
	 */
	callback: async (
		params: OAuthCallbackRequest,
	): Promise<OAuthCallbackResponse> => {
		const response = await apiClient.post<OAuthCallbackResponse>(
			"/auth/google/callback/",
			params,
		);
		return response.data;
	},

	/**
	 * Link Google account to authenticated user
	 * POST /api/auth/google/link/
	 */
	link: async (params: OAuthLinkRequest): Promise<OAuthLinkResponse> => {
		const response = await apiClient.post<OAuthLinkResponse>(
			"/auth/google/link/",
			params,
		);
		return response.data;
	},

	/**
	 * Unlink Google account
	 * DELETE /api/auth/google/unlink/
	 */
	unlink: async (params: OAuthUnlinkRequest): Promise<OAuthUnlinkResponse> => {
		const response = await apiClient.delete<OAuthUnlinkResponse>(
			"/auth/google/unlink/",
			{ data: params },
		);
		return response.data;
	},
};
