/**
 * Two-Factor Authentication API Client
 * Uses corrected endpoints matching backend implementation
 */

import { apiClient } from "@/features/auth/api/authClient";
import { authStore } from "@/features/auth/store/authStore";
import { API_BASE, getCsrfToken } from "@/lib/httpClient";
import type {
	RecoveryCodesResponse,
	TrustedDevicesResponse,
	TwoFactorMethodRemovalResponse,
	TwoFactorSetupResponse,
	TwoFactorStatusResponse,
	TwoFactorVerifyLoginResponse,
} from "../types";

import type { ApiResponseWithMessages } from "@/types";

function isTwoFactorStatusResponse(
	value: unknown,
): value is TwoFactorStatusResponse {
	return (
		typeof value === "object" &&
		value !== null &&
		"is_enabled" in value &&
		"preferred_method" in value
	);
}

export const twoFactorApi = {
	/**
	 * Initialize 2FA setup
	 * Returns QR code for TOTP or sends OTP for email/SMS
	 */
	initializeSetup: async (
		method: "totp" | "email" | "sms",
		phone_number?: string,
	) => {
		const response = await apiClient.post<TwoFactorSetupResponse>(
			"/auth/2fa/setup/",
			{
				method,
				phone_number,
			},
		);
		return response;
	},

	/**
	 * Verify setup code and enable 2FA
	 * Returns recovery codes
	 */
	verifySetup: async (code: string) => {
		const response = await apiClient.post<RecoveryCodesResponse>(
			"/auth/2fa/verify-setup/",
			{ code },
		);
		return response;
	},

	/**
	 * Get current 2FA status
	 */
	getStatus: async () => {
		const response =
			await apiClient.get<ApiResponseWithMessages<TwoFactorStatusResponse>>(
				"/auth/2fa/status/",
			);
		const payload = (response?.data ?? response) as unknown;

		if (isTwoFactorStatusResponse(payload)) {
			return payload;
		}

		return { is_enabled: false, preferred_method: null };
	},

	/**
	 * Verify 2FA code during login (CORRECTED endpoint name)
	 * Accepts both 6-digit codes and recovery codes
	 * partial_token in body (not Authorization header)
	 */
	verifyLogin: async (
		partial_token: string,
		code: string,
		remember_me = false,
	) => {
		const response = await apiClient.post<
			ApiResponseWithMessages<TwoFactorVerifyLoginResponse>
		>(
			"/auth/2fa/verify-login/",
			{
				partial_token,
				code,
				remember_me,
			},
		);
		return response;
	},

	/**
	 * Request a code to disable 2FA (for email/SMS methods)
	 */
	requestDisableCode: async () => {
		const response = await apiClient.post<{
			method: string;
			message: string;
			expires_in?: number;
		}>("/auth/2fa/disable/request/", {});
		return response;
	},

	/**
	 * Disable 2FA
	 */
	disable: async (code: string) => {
		const response = await apiClient.post<{
			enabled: boolean;
			message: string;
		}>("/auth/2fa/disable/", {
			code,
		});
		return response;
	},

	/**
	 * Generate new recovery codes (invalidates old ones)
	 */
	generateRecoveryCodes: async () => {
		const response = await apiClient.post<RecoveryCodesResponse>(
			"/auth/2fa/recovery-codes/generate/",
			{},
		);
		return response;
	},

	/**
	 * Download recovery codes as TXT or PDF
	 * Uses POST to securely send codes in request body instead of URL
	 */
	downloadRecoveryCodes: async (
		codes: string[],
		format: "txt" | "pdf" = "txt",
	) => {
		// Use the same auth mechanism as apiClient
		const token = authStore.state.accessToken;
		const csrfToken = getCsrfToken();

		// Build headers
		const headers: Record<string, string> = {
			"Content-Type": "application/json",
		};

		if (csrfToken) {
			headers["X-CSRFToken"] = csrfToken;
		}

		if (token) {
			headers.Authorization = `Bearer ${token}`;
		}

		// Make POST request with blob response
		const response = await fetch(
			`${API_BASE}/auth/2fa/recovery-codes/download/`,
			{
				method: "POST",
				headers,
				credentials: "include",
				body: JSON.stringify({ codes, format }),
			},
		);

		if (!response.ok) {
			const errorText = await response.text();
			const reason = errorText || response.statusText;
			throw new Error(
				reason
					? `Failed to download recovery codes: ${reason}`
					: "Failed to download recovery codes.",
			);
		}

		// Get the blob
		const blob = await response.blob();

		// Create download link
		const downloadUrl = window.URL.createObjectURL(blob);
		const link = document.createElement("a");
		link.href = downloadUrl;
		link.download = `tinybeans-recovery-codes.${format}`;
		document.body.appendChild(link);
		link.click();
		document.body.removeChild(link);
		window.URL.revokeObjectURL(downloadUrl);
	},

	/**
	 * Get list of trusted devices
	 */
	getTrustedDevices: async () => {
		const response =
			await apiClient.get<ApiResponseWithMessages<TrustedDevicesResponse>>(
				"/auth/2fa/trusted-devices/",
			);
		const payload = (response?.data ?? response) as Partial<TrustedDevicesResponse>;

		if (payload && Array.isArray(payload.devices)) {
			return { devices: payload.devices };
		}

		return { devices: [] };
	},

	/**
	 * Remove a trusted device
	 */
	removeTrustedDevice: async (device_id: string) => {
		const response = await apiClient.delete<{ message?: string }>(
			`/auth/2fa/trusted-devices/${device_id}/`,
		);
		return response;
	},

	/**
	 * Update preferred 2FA method
	 */
	setPreferredMethod: async (method: "totp" | "email" | "sms") => {
		const response = await apiClient.post<{
			preferred_method: string;
			message: string;
		}>("/auth/2fa/preferred-method/", { method });
		return response;
	},

	/**
	 * Remove a configured 2FA method
	 */
	removeMethod: async (method: "totp" | "sms" | "email") => {
		const response = await apiClient.delete<TwoFactorMethodRemovalResponse>(
			`/auth/2fa/methods/${method}/`,
		);
		return response;
	},
};
