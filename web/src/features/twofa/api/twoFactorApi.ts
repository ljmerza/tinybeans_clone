/**
 * Two-Factor Authentication API Client
 * Uses corrected endpoints matching backend implementation
 */

import { API_BASE, authApi } from "@/features/auth";
import type {
	RecoveryCodesResponse,
	TrustedDevicesResponse,
	TwoFactorMethodRemovalResponse,
	TwoFactorSetupResponse,
	TwoFactorStatusResponse,
	TwoFactorVerifyLoginResponse,
} from "../types";

export const twoFactorApi = {
	/**
	 * Initialize 2FA setup
	 * Returns QR code for TOTP or sends OTP for email/SMS
	 */
	initializeSetup: (method: "totp" | "email" | "sms", phone_number?: string) =>
		authApi.post<TwoFactorSetupResponse>("/auth/2fa/setup/", {
			method,
			phone_number,
		}),

	/**
	 * Verify setup code and enable 2FA
	 * Returns recovery codes
	 */
	verifySetup: (code: string) =>
		authApi.post<RecoveryCodesResponse>("/auth/2fa/verify-setup/", { code }),

	/**
	 * Get current 2FA status
	 */
	getStatus: () => authApi.get<TwoFactorStatusResponse>("/auth/2fa/status/"),

	/**
	 * Verify 2FA code during login (CORRECTED endpoint name)
	 * Accepts both 6-digit codes and recovery codes
	 * partial_token in body (not Authorization header)
	 */
	verifyLogin: (partial_token: string, code: string, remember_me = false) =>
		authApi.post<TwoFactorVerifyLoginResponse>("/auth/2fa/verify-login/", {
			partial_token,
			code,
			remember_me,
		}),

	/**
	 * Request a code to disable 2FA (for email/SMS methods)
	 */
	requestDisableCode: () =>
		authApi.post<{ method: string; message: string; expires_in?: number }>(
			"/auth/2fa/disable/request/",
			{},
		),

	/**
	 * Disable 2FA
	 */
	disable: (code: string) =>
		authApi.post<{ enabled: boolean; message: string }>("/auth/2fa/disable/", {
			code,
		}),

	/**
	 * Generate new recovery codes (invalidates old ones)
	 */
	generateRecoveryCodes: () =>
		authApi.post<RecoveryCodesResponse>("/auth/2fa/recovery-codes/generate/", {}),

	/**
	 * Download recovery codes as TXT or PDF
	 */
	downloadRecoveryCodes: (format: "txt" | "pdf" = "txt") => {
		const url = `${API_BASE}/auth/2fa/recovery-codes/download/?format=${format}`;
		window.open(url, "_blank");
	},

	/**
	 * Get list of trusted devices
	 */
	getTrustedDevices: () =>
		authApi.get<TrustedDevicesResponse>("/auth/2fa/trusted-devices/"),

	/**
	 */
	removeTrustedDevice: (device_id: string) =>
		authApi.delete<{ message?: string }>(`/auth/2fa/trusted-devices/${device_id}/`),

	/**
	 * Update preferred 2FA method
	 */
	setPreferredMethod: (method: "totp" | "email" | "sms") =>
		authApi.post<{ preferred_method: string; message: string }>(
			"/auth/2fa/preferred-method/",
			{ method },
		),

	/**
	 * Remove a configured 2FA method
	 */
	removeMethod: (method: "totp" | "sms" | "email") =>
		authApi.delete<TwoFactorMethodRemovalResponse>(`/auth/2fa/methods/${method}/`),
};
