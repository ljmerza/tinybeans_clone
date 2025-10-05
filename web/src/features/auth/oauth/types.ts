/**
 * Google OAuth Types
 * Based on ADR-010 API specifications and ADR-012 notification system
 */

// ADR-012 Message type
export interface ApiMessage {
	i18n_key: string;
	context: Record<string, any>;
}

export interface OAuthInitiateRequest {
	redirect_uri: string;
}

export interface OAuthInitiateResponse {
	google_oauth_url: string;
	state: string;
	expires_in: number;
	messages?: ApiMessage[];
}

export interface OAuthCallbackRequest {
	code: string;
	state: string;
}

export interface OAuthUser {
	id: number;
	email: string;
	username: string;
	auth_provider: "manual" | "google" | "hybrid";
	google_id: string | null;
	email_verified: boolean;
	google_email?: string;
	google_linked_at?: string;
}

export interface OAuthTokens {
	access: string;
	refresh: string;
}

export interface OAuthCallbackResponse {
	user: OAuthUser;
	tokens: OAuthTokens;
	account_action: "created" | "linked" | "login";
	messages?: ApiMessage[];
}

export interface OAuthLinkRequest {
	code: string;
	state: string;
}

export interface OAuthLinkResponse {
	message: string;
	user: OAuthUser;
	messages?: ApiMessage[];
}

export interface OAuthUnlinkRequest {
	password: string;
}

export interface OAuthUnlinkResponse {
	message: string;
	user: OAuthUser;
	messages?: ApiMessage[];
}

export interface OAuthError {
	error: {
		code: string;
		message: string;
		email?: string;
		help_url?: string;
	};
}

export type OAuthErrorCode =
	| "UNVERIFIED_ACCOUNT_EXISTS"
	| "INVALID_REDIRECT_URI"
	| "INVALID_STATE_TOKEN"
	| "GOOGLE_API_ERROR"
	| "RATE_LIMIT_EXCEEDED"
	| "GOOGLE_ACCOUNT_ALREADY_LINKED"
	| "CANNOT_UNLINK_WITHOUT_PASSWORD"
	| "INVALID_PASSWORD"
	| "UNKNOWN_ERROR";

export interface OAuthErrorInfo {
	title: string;
	message: string;
	action: string | null;
	severity: "error" | "warning" | "info";
}
