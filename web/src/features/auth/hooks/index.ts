import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { apiClient } from "../api/modernAuthClient";
import { authStore, setAccessToken } from "../store/authStore";
import type {
	LoginRequest,
	LoginResponse,
	MagicLoginRequest,
	MagicLoginRequestResponse,
	MagicLoginVerifyRequest,
	MagicLoginVerifyResponse,
	MeResponse,
	SignupRequest,
	SignupResponse,
	TwoFactorNavigateState,
} from "../types";

export function useMe() {
	return useQuery({
		queryKey: ["auth", "me", authStore.state.accessToken],
		queryFn: async () => {
			const data = await apiClient.get<MeResponse>("/users/me/");
			return data.user;
		},
		staleTime: 5 * 60 * 1000,
		retry: false,
	});
}

export function useLogin() {
	const qc = useQueryClient();
	const navigate = useNavigate();

	return useMutation<LoginResponse, Error, LoginRequest>({
		mutationFn: async (body) => {
			// Clear any existing auth token before attempting login
			// This prevents 403 errors when user already has a valid token but wants to re-login
			setAccessToken(null);
			return apiClient.post<LoginResponse>("/auth/login/", body);
		},
		onSuccess: (data) => {
			console.log("Login response:", data); // Debug log

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
			navigate({ to: "/" });
		},
		onError: (error) => {
			console.error("Login error:", error); // Debug log
		},
	});
}

export function useSignup() {
	const qc = useQueryClient();
	return useMutation<SignupResponse, Error, SignupRequest>({
		mutationFn: (body) =>
			apiClient.post<SignupResponse>("/auth/signup/", body),
		onSuccess: (data) => {
			setAccessToken(data.tokens.access);
			qc.invalidateQueries({ queryKey: ["auth"] });
		},
	});
}

export function useLogout() {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: async () => {
			await apiClient.post("/auth/logout/");
			setAccessToken(null);
			return true;
		},
		onSuccess: () => {
			qc.invalidateQueries({ queryKey: ["auth"] });
		},
	});
}

type PasswordResetRequestBody = {
	identifier: string;
};

type PasswordResetRequestResponse = {
	message?: string;
	detail?: string;
};

export function usePasswordResetRequest() {
	return useMutation<
		PasswordResetRequestResponse,
		Error,
		PasswordResetRequestBody
	>({
		mutationFn: (body) =>
			apiClient.post<PasswordResetRequestResponse>(
				"/auth/password/reset/request/",
				body,
			),
	});
}

type PasswordResetConfirmBody = {
	token: string;
	password: string;
	password_confirm: string;
};

type PasswordResetConfirmResponse = {
	detail?: string;
};

export function usePasswordResetConfirm() {
	return useMutation<
		PasswordResetConfirmResponse,
		Error,
		PasswordResetConfirmBody
	>({
		mutationFn: (body) =>
			apiClient.post<PasswordResetConfirmResponse>(
				"/auth/password/reset/confirm/",
				body,
			),
	});
}

export function useMagicLoginRequest() {
	return useMutation<MagicLoginRequestResponse, Error, MagicLoginRequest>({
		mutationFn: (body) =>
			apiClient.post<MagicLoginRequestResponse>("/auth/magic-login/request/", body),
	});
}

export function useMagicLoginVerify() {
	const qc = useQueryClient();
	const navigate = useNavigate();

	return useMutation<MagicLoginVerifyResponse, Error, MagicLoginVerifyRequest>({
		mutationFn: (body) =>
			apiClient.post<MagicLoginVerifyResponse>(
				"/auth/magic-login/verify/",
				body,
			),
		onSuccess: (data) => {
			console.log("Magic login response:", data);

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
			navigate({ to: "/" });
		},
	});
}
