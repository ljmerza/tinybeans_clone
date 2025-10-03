import type { TwoFactorMethod, TwoFactorVerifyState } from "@/features/twofa";

export interface AuthTokens {
	access: string;
}

export interface AuthUser {
	id: number;
	username: string;
	email: string;
}

export interface LoginRequest {
	username: string;
	password: string;
}

export interface LoginRequiresTwoFactor {
	requires_2fa: true;
	partial_token: string;
	method: TwoFactorMethod;
	message?: string;
	trusted_device?: false;
	tokens?: undefined;
}

export interface LoginSuccess {
	requires_2fa: false;
	trusted_device: boolean;
	tokens: AuthTokens;
	method?: TwoFactorMethod;
	message?: string;
	partial_token?: undefined;
}

export type LoginResponse = LoginRequiresTwoFactor | LoginSuccess;

export interface SignupRequest {
	username: string;
	email: string;
	password: string;
}

export interface SignupResponse {
	user: AuthUser;
	tokens: AuthTokens;
}

export interface MeResponse {
	user: AuthUser;
}

export type TwoFactorNavigateState = TwoFactorVerifyState;

export interface RefreshAccessTokenResponse {
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
