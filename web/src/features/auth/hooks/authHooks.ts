import {
	consumeInviteRedirect,
	parseInvitationRedirect,
} from "@/features/circles/utils/inviteAnalytics";
import { useApiMessages } from "@/i18n";
import type { ApiError, ApiResponseWithMessages } from "@/types";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { authKeys } from "../api/queryKeys";
import { authServices } from "../api/services";
import { setAccessToken } from "../store/authStore";
import type {
	LoginRequest,
	LoginResponse,
	SignupRequest,
	SignupResponse,
} from "../types";
import { handleTwoFactorRedirect } from "../utils";

function tryNavigateRedirect(
	navigate: ReturnType<typeof useNavigate>,
	target?: string | null,
): boolean {
	if (!target || typeof window === "undefined") {
		return false;
	}

	try {
		const invitationRedirect = parseInvitationRedirect(target);
		if (invitationRedirect) {
			navigate({
				to: "/invitations/accept",
				search: { token: invitationRedirect.token },
			});
			return true;
		}

		window.location.assign(target);
		return true;
	} catch (error) {
		console.warn("Failed to navigate to redirect target", error);
		return false;
	}
}

export function useLogin(options?: { redirect?: string }) {
	const qc = useQueryClient();
	const navigate = useNavigate();
	const { showAsToast } = useApiMessages();

	return useMutation<
		ApiResponseWithMessages<LoginResponse>,
		ApiError,
		LoginRequest
	>({
		mutationFn: async (body) => {
			setAccessToken(null);
			return authServices.login(body);
		},
		onSuccess: (response) => {
			const payload = (response.data ?? response) as LoginResponse;
			const redirectState = handleTwoFactorRedirect(payload);
			if (redirectState) {
				navigate({
					to: "/profile/2fa/verify",
					state: (previous) => ({
						...previous,
						twoFactor: redirectState,
					}),
				});
				return;
			}

			const tokens = payload.tokens ?? response.tokens;
			if (tokens?.access) {
				setAccessToken(tokens.access);
			}
			qc.invalidateQueries({ queryKey: authKeys.session() });

			const messages = response.messages ?? payload.messages;
			if (messages?.length) {
				showAsToast(messages, 200);
			}

			const needsOnboarding =
				"needs_circle_onboarding" in payload &&
				Boolean(
					(payload as typeof payload & { needs_circle_onboarding?: boolean })
						.needs_circle_onboarding,
				);
			if (needsOnboarding) {
				navigate({ to: "/circles/onboarding" });
				return;
			}

			const redirectTarget = options?.redirect ?? consumeInviteRedirect();
			if (tryNavigateRedirect(navigate, redirectTarget)) {
				return;
			}

			navigate({ to: "/" });
		},
		onError: (error) => {
			console.error("Login error:", error);
		},
	});
}

export function useSignup(options?: { redirect?: string }) {
	const qc = useQueryClient();
	const navigate = useNavigate();
	const { showAsToast } = useApiMessages();

	return useMutation<
		ApiResponseWithMessages<SignupResponse>,
		ApiError,
		SignupRequest
	>({
		mutationFn: (body) => authServices.signup(body),
		onSuccess: (response) => {
			const payload = (response.data ??
				(response as unknown as SignupResponse)) as SignupResponse | undefined;

			const tokens = payload?.tokens ?? response.tokens;
			if (tokens?.access) {
				setAccessToken(tokens.access);
			}

			qc.invalidateQueries({ queryKey: authKeys.session() });

			if (response.messages?.length) {
				showAsToast(response.messages, 201);
			}

			const needsOnboarding = Boolean(payload?.needs_circle_onboarding);
			if (needsOnboarding) {
				navigate({ to: "/circles/onboarding" });
				return;
			}

			const redirectTarget = options?.redirect ?? consumeInviteRedirect();
			if (tryNavigateRedirect(navigate, redirectTarget)) {
				return;
			}

			navigate({ to: "/" });
		},
		onError: (error) => {
			console.error("Signup error:", error);
		},
	});
}

export function useLogout() {
	const qc = useQueryClient();

	return useMutation({
		mutationFn: async () => {
			await authServices.logout();
			setAccessToken(null);
			return true;
		},
		onSuccess: () => {
			qc.invalidateQueries({ queryKey: authKeys.session() });
		},
	});
}

export function usePasswordResetRequest() {
	return useMutation<ApiResponseWithMessages, ApiError, { identifier: string }>(
		{
			mutationFn: (body) => authServices.requestPasswordReset(body),
			onError: (error) => {
				console.error("Password reset error:", error);
			},
		},
	);
}

export function usePasswordResetConfirm() {
	return useMutation<
		ApiResponseWithMessages,
		ApiError,
		{
			token: string;
			password: string;
			password_confirm: string;
		}
	>({
		mutationFn: (body) => authServices.confirmPasswordReset(body),
		onError: (error) => {
			console.error("Password reset confirm error:", error);
		},
	});
}

export function useMagicLinkRequest() {
	return useMutation<ApiResponseWithMessages, ApiError, { email: string }>({
		mutationFn: (body) => authServices.requestMagicLink(body),
		onError: (error) => {
			console.error("Magic link request error:", error);
		},
	});
}

export function useMagicLoginVerify(options?: { redirect?: string }) {
	const qc = useQueryClient();
	const navigate = useNavigate();

	return useMutation<ApiResponseWithMessages, ApiError, { token: string }>({
		mutationFn: (body) => authServices.verifyMagicLogin(body),
		onSuccess: (data) => {
			if (data?.tokens?.access) {
				setAccessToken(data.tokens.access);
			}

			qc.invalidateQueries({ queryKey: authKeys.session() });

			const redirectTarget = options?.redirect ?? consumeInviteRedirect();
			if (tryNavigateRedirect(navigate, redirectTarget)) {
				return;
			}

			navigate({ to: "/" });
		},
		onError: (error) => {
			console.error("Magic login verify error:", error);
		},
	});
}
