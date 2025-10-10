import { useApiMessages } from "@/i18n";
import type { ApiError, ApiResponseWithMessages } from "@/types";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { apiClient } from "../api/authClient";
import { authKeys } from "../api/queryKeys";
import { setAccessToken } from "../store/authStore";
import type {
	LoginRequest,
	LoginResponse,
	SignupRequest,
	SignupResponse,
} from "../types";
import { handleTwoFactorRedirect } from "../utils";

export function useLogin() {
	const qc = useQueryClient();
	const navigate = useNavigate();
	const { showAsToast } = useApiMessages();

	return useMutation<ApiResponseWithMessages<LoginResponse>, ApiError, LoginRequest>({
		mutationFn: async (body) => {
			setAccessToken(null);
			return apiClient.post<ApiResponseWithMessages<LoginResponse>>(
				"/auth/login/",
				body,
			);
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

			navigate({ to: "/" });
		},
		onError: (error) => {
			console.error("Login error:", error);
		},
	});
}

export function useSignup() {
	const qc = useQueryClient();
	const { showAsToast } = useApiMessages();

	return useMutation<SignupResponse, ApiError, SignupRequest>({
		mutationFn: (body) => apiClient.post<SignupResponse>("/auth/signup/", body),
		onSuccess: (data) => {
			if (data.tokens?.access) {
				setAccessToken(data.tokens.access);
			}
			qc.invalidateQueries({ queryKey: authKeys.session() });

			if (data.messages?.length) {
				showAsToast(data.messages, 201);
			}
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
			await apiClient.post("/auth/logout/", {});
			setAccessToken(null);
			return true;
		},
		onSuccess: () => {
			qc.invalidateQueries({ queryKey: authKeys.session() });
		},
	});
}

export function usePasswordResetRequest() {
	const { showAsToast } = useApiMessages();

	return useMutation<ApiResponseWithMessages, ApiError, { identifier: string }>(
		{
			mutationFn: (body) =>
				apiClient.post<ApiResponseWithMessages>(
					"/auth/password/reset/request/",
					body,
				),
			onSuccess: (data) => {
				if (data?.messages?.length) {
					showAsToast(data.messages, 200);
				}
			},
			onError: (error) => {
				console.error("Password reset error:", error);
			},
		},
	);
}

export function usePasswordResetConfirm() {
	const { showAsToast } = useApiMessages();

	return useMutation<
		ApiResponseWithMessages,
		ApiError,
		{
			token: string;
			password: string;
			password_confirm: string;
		}
	>({
		mutationFn: (body) =>
			apiClient.post<ApiResponseWithMessages>(
				"/auth/password/reset/confirm/",
				body,
			),
		onSuccess: (data) => {
			if (data?.messages?.length) {
				showAsToast(data.messages, 200);
			}
		},
		onError: (error) => {
			console.error("Password reset confirm error:", error);
		},
	});
}

export function useMagicLinkRequest() {
	return useMutation<ApiResponseWithMessages, ApiError, { email: string }>(
		{
			mutationFn: (body) =>
				apiClient.post<ApiResponseWithMessages>(
					"/auth/magic-login/request/",
					body,
				),
			onError: (error) => {
				console.error("Magic link request error:", error);
			},
		},
	);
}

export function useMagicLoginVerify() {
	const qc = useQueryClient();
	const navigate = useNavigate();
	const { showAsToast } = useApiMessages();

	return useMutation<ApiResponseWithMessages, ApiError, { token: string }>(
		{
			mutationFn: (body) =>
				apiClient.post<ApiResponseWithMessages>(
					"/auth/magic-login/verify/",
					body,
				),
			onSuccess: (data) => {
				if (data?.tokens?.access) {
					setAccessToken(data.tokens.access);
				}

				qc.invalidateQueries({ queryKey: authKeys.session() });

				if (data?.messages?.length) {
					showAsToast(data.messages, 200);
				}

				navigate({ to: "/" });
			},
			onError: (error) => {
				console.error("Magic login verify error:", error);
			},
		},
	);
}
