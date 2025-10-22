import { circleServices } from "@/features/circles/api/services";
import type { CircleInvitationFinalizeResponse } from "@/features/circles/types";
import {
	clearInvitation,
	loadInvitation,
} from "@/features/circles/utils/invitationStorage";
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

type FinalizeResult =
	| { status: "none" }
	| {
			status: "success";
			response: ApiResponseWithMessages<CircleInvitationFinalizeResponse>;
	  }
	| { status: "error"; error: ApiError };

async function finalizeCircleInvitation(
	showAsToast: ReturnType<typeof useApiMessages>["showAsToast"],
	fallbackToken?: string,
): Promise<FinalizeResult> {
	const storedInvitation = loadInvitation();
	const onboardingToken = storedInvitation?.onboardingToken ?? fallbackToken;
	if (!onboardingToken) {
		return { status: "none" };
	}

	try {
		const finalizeResponse =
			await circleServices.finalizeInvitation(onboardingToken);
		if (
			!fallbackToken ||
			storedInvitation?.onboardingToken === onboardingToken
		) {
			clearInvitation();
		}
		if (finalizeResponse.messages?.length) {
			showAsToast(finalizeResponse.messages, 201);
		}
		return { status: "success", response: finalizeResponse };
	} catch (error) {
		const apiError = error as ApiError;
		showAsToast(apiError.messages, apiError.status ?? 400);
		return { status: "error", error: apiError };
	}
}

function tryNavigateRedirect(
	navigate: ReturnType<typeof useNavigate>,
	target?: string | null,
): boolean {
	if (!target || typeof window === "undefined") {
		return false;
	}

	if (typeof target !== "string") {
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
		mutationKey: authKeys.mutations.login(),
		mutationFn: async (body) => {
			setAccessToken(null);
			return authServices.login(body);
		},
		onSuccess: async (response) => {
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
			const invitationRedirect = parseInvitationRedirect(redirectTarget);
			const finalizeResult = await finalizeCircleInvitation(
				showAsToast,
				invitationRedirect?.onboardingToken,
			);
			if (invitationRedirect) {
				if (finalizeResult.status === "success") {
					const finalizeData =
						finalizeResult.response.data ??
						(finalizeResult.response as unknown as CircleInvitationFinalizeResponse);
					const circleId = finalizeData?.circle?.id;
					if (circleId != null) {
						navigate({
							to: "/circles/$circleId",
							params: { circleId: String(circleId) },
						});
					} else {
						navigate({ to: "/circles" });
					}
					return;
				}
				if (tryNavigateRedirect(navigate, redirectTarget)) {
					return;
				}
			}
			if (finalizeResult.status === "success") {
				const finalizeData =
					finalizeResult.response.data ??
					(finalizeResult.response as unknown as CircleInvitationFinalizeResponse);
				const circleId = finalizeData?.circle?.id;
				if (circleId != null) {
					navigate({
						to: "/circles/$circleId",
						params: { circleId: String(circleId) },
					});
					return;
				}
			}
			if (tryNavigateRedirect(navigate, redirectTarget)) {
				return;
			}

			navigate({ to: "/" });
		},
		onError: (error) => {
			console.error("Login error:", error);
		},
		meta: {
			analyticsEvent: "auth:login",
			toast: {
				useResponseMessages: true,
				success: {
					key: "auth.login.login_success",
					status: 200,
				},
				error: {
					key: "auth.login.login_failed",
					status: 400,
				},
			},
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
		mutationKey: authKeys.mutations.signup(),
		mutationFn: (body) => authServices.signup(body),
		onSuccess: async (response) => {
			const payload = (response.data ??
				(response as unknown as SignupResponse)) as SignupResponse | undefined;

			const tokens = payload?.tokens ?? response.tokens;
			if (tokens?.access) {
				setAccessToken(tokens.access);
			}

			qc.invalidateQueries({ queryKey: authKeys.session() });

			const redirectTarget = options?.redirect ?? consumeInviteRedirect();
			const invitationRedirect = parseInvitationRedirect(redirectTarget);
			const finalizeResult = await finalizeCircleInvitation(
				showAsToast,
				invitationRedirect?.onboardingToken,
			);

			const needsOnboarding = Boolean(payload?.needs_circle_onboarding);
			if (needsOnboarding) {
				navigate({ to: "/circles/onboarding" });
				return;
			}

			if (invitationRedirect) {
				if (finalizeResult.status === "success") {
					const finalizeData =
						finalizeResult.response.data ??
						(finalizeResult.response as unknown as CircleInvitationFinalizeResponse);
					const circleId = finalizeData?.circle?.id;
					if (circleId != null) {
						navigate({
							to: "/circles/$circleId",
							params: { circleId: String(circleId) },
						});
					} else {
						navigate({ to: "/circles" });
					}
					return;
				}

				// Finalization not completed; fall back to invitation accept flow.
				navigate({
					to: "/invitations/accept",
					search: {
						token: invitationRedirect.token,
					},
				});
				return;
			}

			if (finalizeResult.status === "success") {
				const finalizeData =
					finalizeResult.response.data ??
					(finalizeResult.response as unknown as CircleInvitationFinalizeResponse);
				const circleId = finalizeData?.circle?.id;
				if (circleId != null) {
					navigate({
						to: "/circles/$circleId",
						params: { circleId: String(circleId) },
					});
					return;
				}
			}
			if (tryNavigateRedirect(navigate, redirectTarget)) {
				return;
			}

			navigate({ to: "/" });
		},
		onError: (error) => {
			console.error("Signup error:", error);
		},
		meta: {
			analyticsEvent: "auth:signup",
			toast: {
				useResponseMessages: true,
				success: {
					key: "auth.signup.signup_success",
					status: 201,
				},
				error: {
					key: "auth.signup.signup_failed",
					status: 400,
				},
			},
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
			qc.removeQueries({ queryKey: authKeys.session(), exact: true });
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
