import type { TwoFactorMethod, TwoFactorVerifyState } from "@/features/twofa";
import type { ApiMessage } from "@/types";

export interface AuthTokens {
	access: string;
}

export type CircleOnboardingStatus = "pending" | "completed" | "dismissed";

export interface AuthUser {
	id: number;
	email: string;
	first_name?: string;
	last_name?: string;
	display_name?: string;
	email_verified?: boolean;
	language?: string;
	role?: string;
	circle_onboarding_status?: CircleOnboardingStatus;
	circle_onboarding_updated_at?: string | null;
	needs_circle_onboarding?: boolean;
	[key: string]: unknown;
}

export interface LoginRequest {
	email: string;
	password: string;
}

export interface LoginRequiresTwoFactor {
	requires_2fa: true;
	partial_token: string;
	method: TwoFactorMethod;
	message?: string;
	messages?: ApiMessage[];
	trusted_device?: false;
	tokens?: undefined;
}

export interface LoginSuccess extends AuthUser {
	requires_2fa?: false;
	trusted_device?: boolean;
	tokens: AuthTokens;
	method?: TwoFactorMethod;
	message?: string;
	messages?: ApiMessage[];
	partial_token?: undefined;
}

export type LoginResponse = LoginRequiresTwoFactor | LoginSuccess;

export interface SignupRequest {
	first_name: string;
	last_name: string;
	email: string;
	password: string;
}

export type SignupResponse = AuthUser & {
	tokens: AuthTokens;
};

export interface MeResponse {
	user: AuthUser;
}

export type TwoFactorNavigateState = TwoFactorVerifyState;

export interface RefreshAccessTokenResponse {
	// Backend wraps response in { data: { access: "..." } }
	data?: {
		access: string;
	};
	// Also support unwrapped format for backwards compatibility
	access?: string;
}

export interface MagicLoginRequest {
	email: string;
}

export interface MagicLoginRequestResponse {
	message: string;
}

export interface MagicLoginVerifyRequest {
	token: string;
}

export type MagicLoginVerifyResponse = LoginRequiresTwoFactor | LoginSuccess;

export interface EmailVerificationConfirmResponse {
	user: AuthUser;
	access_token: string;
	redirect_url: string;
}
