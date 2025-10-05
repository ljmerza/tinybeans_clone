/**
 * Auth Hooks with Explicit Message Handling
 *
 * These hooks provide explicit control over message display for context-aware notifications.
 * Components decide when and how to show success/error messages.
 */
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { useApiMessages } from "@/i18n";
import { apiClient } from "../api/authClient";
import { setAccessToken } from "../store/authStore";
import { handleTwoFactorRedirect } from "../utils";
import type {
	LoginRequest,
	LoginResponse,
	SignupRequest,
	SignupResponse,
} from "../types";
import type { MutationResponse, ApiError } from "@/types";

/**
 * Login hook with explicit message handling
 */
export function useLogin() {
	const qc = useQueryClient();
	const navigate = useNavigate();
	const { showAsToast } = useApiMessages();

	return useMutation<LoginResponse, Error, LoginRequest>({
		mutationFn: async (body) => {
			// Clear any existing auth token
			setAccessToken(null);
			return apiClient.post<LoginResponse>("/auth/login/", body);
		},
		onSuccess: ({ data }: MutationResponse<LoginResponse>) => {
			console.log("Login response:", data);

			// Check if 2FA is required
			if (handleTwoFactorRedirect(data, navigate)) {
				return;
			}

			setAccessToken(data.tokens.access);
			qc.invalidateQueries({ queryKey: ["auth"] });

			// Show success message if provided
			if (data.messages) {
				showAsToast(data.messages, 200);
			}

			navigate({ to: "/" });
		},
		onError: (error: ApiError) => {
			console.error("Login error:", error);
			// Error messages handled by component for inline display
		},
	});
}

/**
 * Signup hook with explicit message handling
 */
export function useSignup() {
	const qc = useQueryClient();
	const { showAsToast } = useApiMessages();

	return useMutation<SignupResponse, Error, SignupRequest>({
		mutationFn: (body) => apiClient.post<SignupResponse>("/auth/signup/", body),
		onSuccess: (data) => {
			setAccessToken(data.tokens.access);
			qc.invalidateQueries({ queryKey: ["auth"] });

			// Show success message
			if (data.messages) {
				showAsToast(data.messages, 201);
			}
		},
		onError: (error: ApiError) => {
			console.error("Signup error:", error);
			// Error messages handled by component
		},
	});
}

/**
 * * logout hook with explicit message handling
 */
export function useLogout() {
	const qc = useQueryClient();
	const { showAsToast } = useApiMessages();

	return useMutation({
		mutationFn: async () => {
			await apiClient.post("/auth/logout/", {});
			setAccessToken(null);
			return true;
		},
		onSuccess: (data: boolean) => {
			qc.invalidateQueries({ queryKey: ["auth"] });

			// Show logout confirmation
			if (data) {
				// Logout successful
			}
		},
	});
}

/**
 * * password reset request hook
 */
export function usePasswordResetRequest() {
	const { showAsToast } = useApiMessages();

	return useMutation<ApiResponseWithMessages, Error, { identifier: string }>({
		mutationFn: (body) => apiClient.post("/auth/password/reset/request/", body),
		onSuccess: (data) => {
			// Show success message
			if (data?.messages) {
				showAsToast(data.messages, 200);
			}
		},
		onError: (error: ApiError) => {
			console.error("Password reset error:", error);
			// Error messages handled by component
		},
	});
}

/**
 * * password reset confirm hook
 */
export function usePasswordResetConfirm() {
	const { showAsToast } = useApiMessages();

	return useMutation<
		ApiResponseWithMessages,
		Error,
		{
			token: string;
			password: string;
			password_confirm: string;
		}
	>({
		mutationFn: (body) => apiClient.post("/auth/password/reset/confirm/", body),
		onSuccess: (data) => {
			// Show success message
			if (data?.messages) {
				showAsToast(data.messages, 200);
			}
		},
		onError: (error: ApiError) => {
			console.error("Password reset confirm error:", error);
			// Error messages handled by component
		},
	});
}

/**
 * * magic link request hook
 */
export function useMagicLinkRequest() {
	const { showAsToast } = useApiMessages();

	return useMutation<ApiResponseWithMessages, Error, { email: string }>({
		mutationFn: (body) => apiClient.post("/auth/magic-login/request/", body),
		onError: (error: ApiError) => {
			console.error("Magic link request error:", error);
		},
	});
}

/**
 * * magic login verify hook
 */
export function useMagicLoginVerify() {
	const qc = useQueryClient();
	const navigate = useNavigate();
	const { showAsToast } = useApiMessages();

	return useMutation<ApiResponseWithMessages, Error, { token: string }>({
		mutationFn: (body) => apiClient.post("/auth/magic-login/verify/", body),
		onSuccess: (data) => {
			// Set auth token
			if (data?.tokens?.access) {
				setAccessToken(data.tokens.access);
			}

			qc.invalidateQueries({ queryKey: ["auth"] });

			// Show success message
			if (data?.messages) {
				showAsToast(data.messages, 200);
			}

			// Navigate to home
			navigate({ to: "/" });
		},
		onError: (error: ApiError) => {
			console.error("Magic login verify error:", error);
			// Error messages handled by component
		},
	});
}
