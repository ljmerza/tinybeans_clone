import type { ApiResponseWithMessages } from "@/types";
import type {
	EmailVerificationConfirmResponse,
	LoginRequest,
	LoginResponse,
	MagicLoginRequest,
	MagicLoginRequestResponse,
	MagicLoginVerifyRequest,
	MagicLoginVerifyResponse,
	MeResponse,
	SignupRequest,
	SignupResponse,
} from "../types";
import type { RequestOptions as AuthRequestOptions } from "./authClient";
import { apiClient } from "./authClient";

export interface PasswordResetRequest {
	identifier: string;
}

export interface PasswordResetConfirmRequest {
	token: string;
	password: string;
	password_confirm: string;
}

export interface VerifyEmailConfirmRequest {
	token: string;
}

export const authServices = {
	getSession(options?: AuthRequestOptions) {
		return apiClient.get<ApiResponseWithMessages<MeResponse>>(
			"/users/me/",
			options,
		);
	},

	login(body: LoginRequest) {
		return apiClient.post<ApiResponseWithMessages<LoginResponse>>(
			"/auth/login/",
			body,
		);
	},

	signup(body: SignupRequest) {
		return apiClient.post<ApiResponseWithMessages<SignupResponse>>(
			"/auth/signup/",
			body,
		);
	},

	logout() {
		return apiClient.post<ApiResponseWithMessages>("/auth/logout/", {});
	},

	requestPasswordReset(body: PasswordResetRequest) {
		return apiClient.post<ApiResponseWithMessages>(
			"/auth/password/reset/request/",
			body,
		);
	},

	confirmPasswordReset(body: PasswordResetConfirmRequest) {
		return apiClient.post<ApiResponseWithMessages>(
			"/auth/password/reset/confirm/",
			body,
		);
	},

	requestMagicLink(body: MagicLoginRequest) {
		return apiClient.post<ApiResponseWithMessages<MagicLoginRequestResponse>>(
			"/auth/magic-login/request/",
			body,
		);
	},

	verifyMagicLogin(body: MagicLoginVerifyRequest) {
		return apiClient.post<ApiResponseWithMessages<MagicLoginVerifyResponse>>(
			"/auth/magic-login/verify/",
			body,
		);
	},

	resendVerificationEmail() {
		return apiClient.post<ApiResponseWithMessages>(
			"/auth/verify-email/resend/",
			{},
		);
	},

	confirmEmailVerification(body: VerifyEmailConfirmRequest) {
		return apiClient.post<
			ApiResponseWithMessages<EmailVerificationConfirmResponse>
		>("/auth/verify-email/confirm/", body);
	},
};
