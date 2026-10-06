import {
	consumeInviteRedirect,
	parseInvitationRedirect,
} from "@/features/circles/utils/inviteAnalytics";
import { useApiMessages } from "@/i18n";
import { getBrowserLanguage } from "@/i18n/browserLanguage";
import type { ApiError } from "@/types";
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { setAccessToken } from "../store/authStore";
import {
	clearAppleOAuthState,
	getAppleRedirectUri,
	storeAppleOAuthState,
} from "./appleUtils";
import { appleOauthApi } from "./client";
import type { OAuthCallbackRequest } from "./types";

/**
 * useAppleOAuth Hook
 * Sign in with Apple counterpart of useGoogleOAuth
 */
export function useAppleOAuth() {
	const navigate = useNavigate();
	const { handleError, showAsToast } = useApiMessages();

	const initiateMutation = useMutation({
		mutationFn: () =>
			appleOauthApi.initiate({ redirect_uri: getAppleRedirectUri() }),
		onSuccess: (data) => {
			storeAppleOAuthState(data.state);
			window.location.href = data.apple_oauth_url;
		},
		onError: (error: ApiError) => {
			handleError(error);
		},
	});

	const callbackMutation = useMutation({
		mutationFn: (params: OAuthCallbackRequest) =>
			appleOauthApi.callback(params),
		onSuccess: (response) => {
			setAccessToken(response.tokens.access);
			clearAppleOAuthState();

			if (response.messages && response.messages.length > 0) {
				showAsToast(response.messages, 200);
			}

			const redirectTarget = consumeInviteRedirect();
			if (redirectTarget) {
				const invitationRedirect = parseInvitationRedirect(redirectTarget);
				if (invitationRedirect) {
					navigate({
						to: "/invitations/accept",
						search: { token: invitationRedirect.token },
					});
					return;
				}
				window.location.assign(redirectTarget);
				return;
			}

			navigate({ to: "/" });
		},
		onError: (error: ApiError) => {
			console.error("Apple OAuth callback error:", error);
			clearAppleOAuthState();
		},
	});

	const linkMutation = useMutation({
		mutationFn: (params: OAuthCallbackRequest) => appleOauthApi.link(params),
		onSuccess: (response) => {
			clearAppleOAuthState();
			if (response.messages && response.messages.length > 0) {
				showAsToast(response.messages, 200);
			}
		},
		onError: (error: ApiError) => {
			handleError(error);
			clearAppleOAuthState();
		},
	});

	const unlinkMutation = useMutation({
		mutationFn: (password: string) => appleOauthApi.unlink({ password }),
		onSuccess: (response) => {
			if (response.messages && response.messages.length > 0) {
				showAsToast(response.messages, 200);
			}
		},
		onError: (error: ApiError) => {
			handleError(error);
		},
	});

	return {
		initiateOAuth: () => initiateMutation.mutate(),
		handleCallback: (code: string, state: string) =>
			callbackMutation.mutate({
				code,
				state,
				language: getBrowserLanguage(),
			}),
		linkAppleAccount: (code: string, state: string) =>
			linkMutation.mutate({ code, state }),
		unlinkAppleAccount: (password: string) => unlinkMutation.mutate(password),

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
