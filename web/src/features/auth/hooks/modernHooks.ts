/**
 * Modern Auth Hooks (ADR-012 Compliant)
 * 
 * These hooks use the new notification strategy with explicit message handling.
 * Use these for new components. Legacy hooks are in index.ts for backward compatibility.
 */
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { useApiMessages } from "@/i18n";
import { apiClient } from "../api/modernAuthClient";
import { setAccessToken } from "../store/authStore";
import type {
	LoginRequest,
	LoginResponse,
	SignupRequest,
	SignupResponse,
	TwoFactorNavigateState,
} from "../types";

/**
 * Modern login hook with explicit message handling
 */
export function useLoginModern() {
	const qc = useQueryClient();
	const navigate = useNavigate();
	const { showAsToast } = useApiMessages();

	return useMutation<LoginResponse, Error, LoginRequest>({
		mutationFn: async (body) => {
			// Clear any existing auth token
			setAccessToken(null);
			return apiClient.post<LoginResponse>("/auth/login/", body);
		},
		onSuccess: ({ data }:any) => {
			console.log("Login response:", data);

			// Check if 2FA is required
			if (data.requires_2fa) {
				const state: TwoFactorNavigateState = {
					partialToken: data.partial_token,
					method: data.method,
					message: data.message,
				};
				navigate({ to: "/2fa/verify", state: state as never });
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
		onError: (error: any) => {
			console.error("Login error:", error);
			// Error messages handled by component for inline display
		},
	});
}

/**
 * Modern signup hook with explicit message handling
 */
export function useSignupModern() {
	const qc = useQueryClient();
	const { showAsToast } = useApiMessages();

	return useMutation<SignupResponse, Error, SignupRequest>({
		mutationFn: (body) =>
			apiClient.post<SignupResponse>("/auth/signup/", body),
		onSuccess: (data) => {
			setAccessToken(data.tokens.access);
			qc.invalidateQueries({ queryKey: ["auth"] });
			
			// Show success message
			if (data.messages) {
				showAsToast(data.messages, 201);
			}
		},
		onError: (error: any) => {
			console.error("Signup error:", error);
			// Error messages handled by component
		},
	});
}

/**
 * Modern logout hook with explicit message handling
 */
export function useLogoutModern() {
	const qc = useQueryClient();
	const { showAsToast } = useApiMessages();

	return useMutation({
		mutationFn: async () => {
			await apiClient.post("/auth/logout/", {});
			setAccessToken(null);
			return true;
		},
		onSuccess: (data: any) => {
			qc.invalidateQueries({ queryKey: ["auth"] });
			
			// Show logout confirmation
			if (data?.messages) {
				showAsToast(data.messages, 200);
			}
		},
	});
}

/**
 * Modern password reset request hook
 */
export function usePasswordResetRequestModern() {
	const { showAsToast } = useApiMessages();

	return useMutation<any, Error, { identifier: string }>({
		mutationFn: (body) =>
			apiClient.post("/auth/password/reset/request/", body),
		onSuccess: (data) => {
			// Show success message
			if (data?.messages) {
				showAsToast(data.messages, 200);
			}
		},
		onError: (error: any) => {
			console.error("Password reset error:", error);
			// Error messages handled by component
		},
	});
}

/**
 * Modern password reset confirm hook
 */
export function usePasswordResetConfirmModern() {
	const { showAsToast } = useApiMessages();

	return useMutation<any, Error, {
		token: string;
		password: string;
		password_confirm: string;
	}>({
		mutationFn: (body) =>
			apiClient.post("/auth/password/reset/confirm/", body),
		onSuccess: (data) => {
			// Show success message
			if (data?.messages) {
				showAsToast(data.messages, 200);
			}
		},
		onError: (error: any) => {
			console.error("Password reset confirm error:", error);
			// Error messages handled by component
		},
	});
}

/**
 * Modern magic link request hook
 */
export function useMagicLinkRequestModern() {
	const { showAsToast } = useApiMessages();

	return useMutation<any, Error, { email: string }>({
		mutationFn: (body) =>
			apiClient.post("/auth/magic-login/request/", body),
		onSuccess: (data) => {
			// Show success message (always shown for security)
			if (data?.messages) {
				showAsToast(data.messages, 202);
			}
		},
		onError: (error: any) => {
			console.error("Magic link request error:", error);
			// Error messages handled by component
		},
	});
}

/**
 * Modern magic login verify hook
 */
export function useMagicLoginVerifyModern() {
	const qc = useQueryClient();
	const navigate = useNavigate();
	const { showAsToast } = useApiMessages();

	return useMutation<any, Error, { token: string }>({
		mutationFn: (body) =>
			apiClient.post("/auth/magic-login/verify/", body),
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
		onError: (error: any) => {
			console.error("Magic login verify error:", error);
			// Error messages handled by component
		},
	});
}
