/**
 * Two-Factor Authentication Types
 */

export type TwoFactorMethod = "totp" | "email" | "sms";

export interface TwoFactorSetupRequest {
	method: TwoFactorMethod;
	phone_number?: string;
}

export interface TwoFactorSetupResponse {
	method: TwoFactorMethod;
	secret?: string;
	qr_code?: string;
	qr_code_image?: string;
	message?: string;
	expires_in?: number;
}

export interface TwoFactorVerifyLoginRequest {
	partial_token: string;
	code: string;
	remember_me?: boolean;
}

export interface TwoFactorVerifyLoginResponse {
	user: {
		id: number;
		username: string;
		email: string;
	};
	tokens: {
		access: string;
		// refresh in HTTP-only cookie
	};
	trusted_device: boolean;
}

export interface TwoFactorStatusResponse {
	is_enabled: boolean;
	preferred_method: TwoFactorMethod | null;
	phone_number?: string;
	backup_email?: string;
	created_at?: string;
	updated_at?: string;
	message?: string;
}

export interface RecoveryCodesResponse {
	recovery_codes: string[];
	message: string;
	enabled?: boolean;
	method?: TwoFactorMethod;
}

export interface TrustedDevice {
	device_id: string;
	device_name: string;
	ip_address: string;
	last_used_at: string;
	expires_at: string;
	created_at: string;
}

export interface TrustedDevicesResponse {
	devices: TrustedDevice[];
}

// Router state for 2FA verification page
export interface TwoFactorVerifyState {
	partialToken: string;
	method: TwoFactorMethod;
	message?: string;
}
