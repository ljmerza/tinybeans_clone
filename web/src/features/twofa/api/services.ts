import { apiClient as authApi } from "@/features/auth/api/authClient";
import { authStore } from "@/features/auth/store/authStore";
import { API_BASE, getCsrfToken } from "@/lib/httpClient";
import type { ApiResponseWithMessages } from "@/types";
import type {
	AddTrustedDeviceResponse,
	RecoveryCodesResponse,
	TrustedDevicesResponse,
	TwoFactorMethod,
	TwoFactorMethodRemovalResponse,
	TwoFactorSetupResponse,
	TwoFactorStatusResponse,
	TwoFactorVerifyLoginResponse,
} from "../types";

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

export const twoFactorServices = {
	initializeSetup(method: TwoFactorMethod, phoneNumber?: string) {
		return authApi.post<TwoFactorSetupResponse>("/auth/2fa/setup/", {
			method,
			phone_number: phoneNumber,
		});
	},

	verifySetup(code: string) {
		return authApi.post<RecoveryCodesResponse>("/auth/2fa/verify-setup/", {
			code,
		});
	},

	async getStatus() {
		const response =
			await authApi.get<ApiResponseWithMessages<TwoFactorStatusResponse>>(
				"/auth/2fa/status/",
			);
		const payload = response?.data ?? response;

		if (isTwoFactorStatusResponse(payload)) {
			return payload;
		}

		return { is_enabled: false, preferred_method: null };
	},

	verifyLogin(partialToken: string, code: string, rememberMe = false) {
		return authApi.post<ApiResponseWithMessages<TwoFactorVerifyLoginResponse>>(
			"/auth/2fa/verify-login/",
			{
				partial_token: partialToken,
				code,
				remember_me: rememberMe,
			},
		);
	},

	requestDisableCode() {
		return authApi.post<{
			method: string;
			message: string;
			expires_in?: number;
		}>("/auth/2fa/disable/request/", {});
	},

	disable(code: string) {
		return authApi.post<{ enabled: boolean; message: string }>(
			"/auth/2fa/disable/",
			{ code },
		);
	},

	generateRecoveryCodes() {
		return authApi.post<RecoveryCodesResponse>(
			"/auth/2fa/recovery-codes/generate/",
			{},
		);
	},

	async downloadRecoveryCodes(codes: string[], format: "txt" | "pdf" = "txt") {
		const token = authStore.state.accessToken;
		const csrfToken = getCsrfToken();

		const headers: Record<string, string> = {
			"Content-Type": "application/json",
		};

		if (csrfToken) {
			headers["X-CSRFToken"] = csrfToken;
		}

		if (token) {
			headers.Authorization = `Bearer ${token}`;
		}

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

		const blob = await response.blob();
		const downloadUrl = window.URL.createObjectURL(blob);
		const link = document.createElement("a");
		link.href = downloadUrl;
		link.download = `tinybeans-recovery-codes.${format}`;
		document.body.appendChild(link);
		link.click();
		document.body.removeChild(link);
		window.URL.revokeObjectURL(downloadUrl);
	},

	async getTrustedDevices() {
		const response = await authApi.get<
			ApiResponseWithMessages<TrustedDevicesResponse>
		>("/auth/2fa/trusted-devices/");
		const payload = response?.data ?? response;
		if (payload && Array.isArray(payload.devices)) {
			return payload;
		}
		return { devices: [] } as TrustedDevicesResponse;
	},

	removeTrustedDevice(deviceId: string) {
		return authApi.delete<{ message?: string }>(
			`/auth/2fa/trusted-devices/${deviceId}/`,
		);
	},

	addTrustedDevice() {
		return authApi.post<ApiResponseWithMessages<AddTrustedDeviceResponse>>(
			"/auth/2fa/trusted-devices/",
			{},
		);
	},

	setPreferredMethod(method: TwoFactorMethod) {
		return authApi.post<{ preferred_method: string; message: string }>(
			"/auth/2fa/preferred-method/",
			{ method },
		);
	},

	removeMethod(method: TwoFactorMethod) {
		return authApi.delete<TwoFactorMethodRemovalResponse>(
			`/auth/2fa/methods/${method}/`,
		);
	},
};
