import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { useApiMessages } from "@/i18n";
import { setAccessToken } from "../store/authStore";
import { oauthApi } from "./client";
import type { OAuthCallbackRequest } from "./types";
import {
	clearOAuthState,
	getRedirectUri,
	storeOAuthState,
} from "./utils";

/**
 * useGoogleOAuth Hook
 * Manages Google OAuth flow state and API calls
 */
export function useGoogleOAuth() {
	const navigate = useNavigate();
	const { handleError, showAsToast } = useApiMessages();

	// Mutation for initiating OAuth flow
	const initiateMutation = useMutation({
		mutationFn: () =>
			oauthApi.initiate({
				redirect_uri: getRedirectUri(),
			}),
		onSuccess: (data) => {
			// Store state in sessionStorage for validation
			storeOAuthState(data.state);
			// Redirect to Google OAuth URL
			window.location.href = data.google_oauth_url;
		},
		onError: (error: any) => {
			// Handle errors with i18n translation
			handleError(error);
		},
	});

	// Mutation for handling OAuth callback
	const callbackMutation = useMutation({
		mutationFn: (params: OAuthCallbackRequest) => oauthApi.callback(params),
		onSuccess: (response) => {
			// Store access token
			setAccessToken(response.tokens.access);

			// Clear stored state
			clearOAuthState();

			// Show success messages if present (optional - backend might not send them)
			if (response.messages && response.messages.length > 0) {
				showAsToast(response.messages, 200);
			}

			// Navigate to home/dashboard (adjust route as needed)
			navigate({ to: "/" });
		},
		onError: (error: any) => {
			// Handle errors with i18n translation
			handleError(error);
			// Clear state on error
			clearOAuthState();
		},
	});

	// Mutation for linking Google account (authenticated users)
	const linkMutation = useMutation({
		mutationFn: (params: OAuthCallbackRequest) => oauthApi.link(params),
		onSuccess: (response) => {
			clearOAuthState();
			// Show success message from backend
			if (response.messages && response.messages.length > 0) {
				showAsToast(response.messages, 200);
			}
		},
		onError: (error: any) => {
			// Handle errors with i18n translation
			handleError(error);
			clearOAuthState();
		},
	});

	// Mutation for unlinking Google account
	const unlinkMutation = useMutation({
		mutationFn: (password: string) => oauthApi.unlink({ password }),
		onSuccess: (response) => {
			// Show success message from backend
			if (response.messages && response.messages.length > 0) {
				showAsToast(response.messages, 200);
			}
		},
		onError: (error: any) => {
			// Handle errors with i18n translation
			handleError(error);
		},
	});

	return {
		// Functions
		initiateOAuth: () => initiateMutation.mutate(),
		handleCallback: (code: string, state: string) =>
			callbackMutation.mutate({ code, state }),
		linkGoogleAccount: (code: string, state: string) =>
			linkMutation.mutate({ code, state }),
		unlinkGoogleAccount: (password: string) => unlinkMutation.mutate(password),

		// State
		isLoading:
			initiateMutation.isPending ||
			callbackMutation.isPending ||
			linkMutation.isPending ||
			unlinkMutation.isPending,
		error:
			initiateMutation.error ||
			callbackMutation.error ||
			linkMutation.error ||
			unlinkMutation.error,
	};
}
