/**
 * Two-Factor Authentication React Query Hooks
 */

import { setAccessToken } from "@/features/auth";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { twoFactorApi } from "../api/twoFactorApi";
import type {
	RecoveryCodesResponse,
	TrustedDevicesResponse,
	TwoFactorMethod,
	TwoFactorMethodRemovalResponse,
	TwoFactorSetupResponse,
	TwoFactorStatusResponse,
	TwoFactorVerifyLoginResponse,
} from "../types";

/**
 * Initialize 2FA setup
 */
export function useInitialize2FASetup() {
	return useMutation<
		TwoFactorSetupResponse,
		Error,
		{ method: TwoFactorMethod; phone_number?: string }
	>({
		mutationFn: ({ method, phone_number }) =>
			twoFactorApi.initializeSetup(method, phone_number),
	});
}

/**
 * Verify setup code and complete 2FA setup
 */
export function useVerify2FASetup() {
	const queryClient = useQueryClient();

	return useMutation<RecoveryCodesResponse, Error, string>({
		mutationFn: (code) => twoFactorApi.verifySetup(code),
		onSuccess: () => {
			// Invalidate status to refresh
			queryClient.invalidateQueries({ queryKey: ["2fa", "status"] });
		},
	});
}

/**
 * Get 2FA status
 */
export function use2FAStatus() {
	return useQuery<TwoFactorStatusResponse>({
		queryKey: ["2fa", "status"],
		queryFn: () => twoFactorApi.getStatus(),
	});
}

/**
 * Verify 2FA code during login
 */
export function useVerify2FALogin() {
	const queryClient = useQueryClient();

	return useMutation<
		TwoFactorVerifyLoginResponse,
		Error,
		{ partial_token: string; code: string; remember_me?: boolean }
	>({
		mutationFn: ({ partial_token, code, remember_me }) =>
			twoFactorApi.verifyLogin(partial_token, code, remember_me),
		onSuccess: async (data) => {
			console.log("2FA verify success:", data); // Debug log

			// Store access token
			if (data.tokens?.access) {
				console.log(
					"Setting access token:",
					`${data.tokens.access.substring(0, 20)}...`,
				); // Debug log
				setAccessToken(data.tokens.access);
			} else {
				console.error("No access token in response:", data); // Debug log
				throw new Error("No access token received");
			}

			// Device ID cookie is set by backend automatically
			if (data.trusted_device) {
				console.log("Device marked as trusted"); // Debug log
			}

			// Invalidate queries to refresh auth state
			await Promise.all([
				queryClient.invalidateQueries({ queryKey: ["user"] }),
				queryClient.invalidateQueries({ queryKey: ["auth"] }),
			]);

			console.log("Authentication successful, navigating to home"); // Debug log
		},
		onError: (error) => {
			console.error("2FA verify error:", error); // Debug log
		},
	});
}

/**
 * Request a code to disable 2FA
 */
export function useRequestDisableCode() {
	return useMutation<
		{ method: string; message: string; expires_in?: number },
		Error
	>({
		mutationFn: () => twoFactorApi.requestDisableCode(),
	});
}

/**
 * Disable 2FA
 */
export function useDisable2FA() {
	const queryClient = useQueryClient();

	return useMutation<{ enabled: boolean; message: string }, Error, string>({
		mutationFn: (code) => twoFactorApi.disable(code),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["2fa", "status"] });
		},
	});
}

/**
 * Generate new recovery codes
 */
export function useGenerateRecoveryCodes() {
	return useMutation<RecoveryCodesResponse, Error>({
		mutationFn: () => twoFactorApi.generateRecoveryCodes(),
	});
}

/**
 * Get trusted devices
 */
export function useTrustedDevices() {
	return useQuery<TrustedDevicesResponse>({
		queryKey: ["2fa", "trusted-devices"],
		queryFn: () => twoFactorApi.getTrustedDevices(),
	});
}

/**
 * Remove a trusted device
 */
export function useRemoveTrustedDevice() {
	const queryClient = useQueryClient();

	return useMutation<{ message?: string }, Error, string>({
		mutationFn: (device_id) => twoFactorApi.removeTrustedDevice(device_id),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["2fa", "trusted-devices"] });
		},
	});
}

/**
 * Update preferred 2FA method
 */
export function useSetPreferredMethod() {
	const queryClient = useQueryClient();

	return useMutation<
		{ preferred_method: string; message: string },
		Error,
		TwoFactorMethod
	>({
		mutationFn: (method) => twoFactorApi.setPreferredMethod(method),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["2fa", "status"] });
		},
	});
}

/**
 * Remove a configured 2FA method
 */
export function useRemoveTwoFactorMethod() {
	const queryClient = useQueryClient();

	return useMutation<TwoFactorMethodRemovalResponse, Error, TwoFactorMethod>({
		mutationFn: (method) => twoFactorApi.removeMethod(method),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["2fa", "status"] });
		},
	});
}
