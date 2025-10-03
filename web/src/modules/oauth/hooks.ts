import { setAccessToken } from "@/modules/login/store";
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { toast } from "sonner";
import { oauthApi } from "./client";
import type { OAuthCallbackRequest } from "./types";
import {
	clearOAuthState,
	getOAuthErrorMessage,
	getRedirectUri,
	storeOAuthState,
} from "./utils";

/**
 * useGoogleOAuth Hook
 * Manages Google OAuth flow state and API calls
 */
export function useGoogleOAuth() {
	const navigate = useNavigate();

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
		onError: (error) => {
			const errorInfo = getOAuthErrorMessage(error);
			toast.error(errorInfo.title, {
				description: errorInfo.message,
			});
		},
	});

	// Mutation for handling OAuth callback
	const callbackMutation = useMutation({
		mutationFn: (params: OAuthCallbackRequest) => oauthApi.callback(params),
		onSuccess: (data) => {
			// Store access token
			setAccessToken(data.tokens.access);

			// Show success message based on action
			const messages = {
				created: "Account created successfully! Welcome to Tinybeans.",
				linked: "Google account linked successfully!",
				login: "Signed in successfully!",
			};
			toast.success(messages[data.account_action]);

			// Clear stored state
			clearOAuthState();

			// Navigate to home/dashboard (adjust route as needed)
			navigate({ to: "/" });
		},
		onError: (error) => {
			const errorInfo = getOAuthErrorMessage(error);
			toast.error(errorInfo.title, {
				description: errorInfo.message,
			});
			// Clear state on error
			clearOAuthState();
		},
	});

	// Mutation for linking Google account (authenticated users)
	const linkMutation = useMutation({
		mutationFn: (params: OAuthCallbackRequest) => oauthApi.link(params),
		onSuccess: () => {
			toast.success("Google account linked successfully!");
			clearOAuthState();
		},
		onError: (error) => {
			const errorInfo = getOAuthErrorMessage(error);
			toast.error(errorInfo.title, {
				description: errorInfo.message,
			});
			clearOAuthState();
		},
	});

	// Mutation for unlinking Google account
	const unlinkMutation = useMutation({
		mutationFn: (password: string) => oauthApi.unlink({ password }),
		onSuccess: () => {
			toast.success("Google account unlinked successfully");
		},
		onError: (error) => {
			const errorInfo = getOAuthErrorMessage(error);
			toast.error(errorInfo.title, {
				description: errorInfo.message,
			});
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
