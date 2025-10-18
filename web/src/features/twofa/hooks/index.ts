/**
 * Two-Factor Authentication React Query Hooks
 */

import { authKeys, setAccessToken, userKeys } from "@/features/auth";
import { extractApiError } from "@/features/auth/utils";
import { useApiMessages } from "@/i18n";
import type { HttpError } from "@/lib/httpClient";
import { showToast } from "@/lib/toast";
import type { ApiResponseWithMessages } from "@/types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { twoFaKeys } from "../api/queryKeys";
import { twoFactorServices } from "../api/services";
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

type ShowAsToastFn = ReturnType<typeof useApiMessages>["showAsToast"];

function notifyMutationError(
	error: unknown,
	fallback: string,
	showAsToast: ShowAsToastFn,
) {
	const httpError = error as HttpError | undefined;
	if (httpError?.messages?.length) {
		showAsToast(httpError.messages, httpError.status ?? 400);
		return;
	}

	const message = extractApiError(error, fallback);
	showToast({ message, level: "error" });
}

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
			twoFactorServices.initializeSetup(method, phone_number),
	});
}

/**
 * Verify setup code and complete 2FA setup
 */
export function useVerify2FASetup() {
	const queryClient = useQueryClient();

	return useMutation<RecoveryCodesResponse, Error, string>({
		mutationFn: (code) => twoFactorServices.verifySetup(code),
		onSuccess: () => {
			// Invalidate status to refresh
			queryClient.invalidateQueries({ queryKey: twoFaKeys.status() });
		},
	});
}

/**
 * Get 2FA status
 */
export function use2FAStatus() {
	return useQuery<TwoFactorStatusResponse>({
		queryKey: twoFaKeys.status(),
		queryFn: () => twoFactorServices.getStatus(),
	});
}

/**
 * Verify 2FA code during login
 */
export function useVerify2FALogin() {
	const queryClient = useQueryClient();
	const { showAsToast } = useApiMessages();
	const { t } = useTranslation();

	return useMutation<
		ApiResponseWithMessages<TwoFactorVerifyLoginResponse>,
		Error,
		{ partial_token: string; code: string; remember_me?: boolean }
	>({
		mutationFn: ({ partial_token, code, remember_me }) =>
			twoFactorServices.verifyLogin(partial_token, code, remember_me),
		onSuccess: async (response) => {
			const payload = (response.data ??
				response) as TwoFactorVerifyLoginResponse;
			// Store access token
			const tokens = payload.tokens ?? response.tokens;
			if (!tokens?.access) {
				throw new Error("No access token received");
			}
			setAccessToken(tokens.access);

			// Device ID cookie is set by backend automatically

			// Invalidate queries to refresh auth state
			await Promise.all([
				queryClient.invalidateQueries({ queryKey: userKeys.profile() }),
				queryClient.invalidateQueries({ queryKey: authKeys.session() }),
			]);
		},
		onError: (error) => {
			notifyMutationError(error, t("twofa.errors.verify_login"), showAsToast);
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
		mutationFn: () => twoFactorServices.requestDisableCode(),
	});
}

/**
 * Disable 2FA
 */
export function useDisable2FA() {
	const queryClient = useQueryClient();
	const { showAsToast } = useApiMessages();
	const { t } = useTranslation();

	return useMutation<{ enabled: boolean; message: string }, Error, string>({
		mutationFn: (code) => twoFactorServices.disable(code),
		onSuccess: (response) => {
			queryClient.invalidateQueries({ queryKey: twoFaKeys.status() });
			if (response?.message) {
				showToast({ message: response.message, level: "success" });
			}
		},
		onError: (error) => {
			notifyMutationError(error, t("twofa.errors.disable"), showAsToast);
		},
	});
}

/**
 * Generate new recovery codes
 */
export function useGenerateRecoveryCodes() {
	const { showAsToast } = useApiMessages();
	const { t } = useTranslation();

	return useMutation<RecoveryCodesResponse, Error>({
		mutationFn: () => twoFactorServices.generateRecoveryCodes(),
		onSuccess: (data) => {
			if (data?.message) {
				showToast({ message: data.message, level: "success" });
			}
		},
		onError: (error) => {
			notifyMutationError(error, t("twofa.errors.generate_codes"), showAsToast);
		},
	});
}

/**
 * Get trusted devices
 */
export function useTrustedDevices() {
	return useQuery<TrustedDevicesResponse>({
		queryKey: twoFaKeys.trustedDevices(),
		queryFn: () => twoFactorServices.getTrustedDevices(),
	});
}

/**
 * Add the current device as trusted
 */
export function useAddTrustedDevice() {
	const queryClient = useQueryClient();
	const { showAsToast } = useApiMessages();
	const { t } = useTranslation();

	return useMutation<
		ApiResponseWithMessages<AddTrustedDeviceResponse>,
		Error,
		void
	>({
		mutationFn: () => twoFactorServices.addTrustedDevice(),
		onSuccess: (response) => {
			queryClient.invalidateQueries({ queryKey: twoFaKeys.trustedDevices() });

			const created = response?.data?.created ?? true;
			if (response?.messages?.length) {
				showAsToast(response.messages, created ? 201 : 200);
			} else {
				showToast({
					message: t(
						created
							? "twofa.messages.trusted_device_added"
							: "twofa.messages.trusted_device_already",
					),
					level: "success",
				});
			}
		},
		onError: (error) => {
			notifyMutationError(
				error,
				t("twofa.errors.add_trusted_device"),
				showAsToast,
			);
		},
	});
}

/**
 * Remove a trusted device
 */
export function useRemoveTrustedDevice() {
	const queryClient = useQueryClient();
	const { showAsToast } = useApiMessages();
	const { t } = useTranslation();

	return useMutation<{ message?: string }, Error, string>({
		mutationFn: (device_id) => twoFactorServices.removeTrustedDevice(device_id),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: twoFaKeys.trustedDevices() });
			showToast({
				message: t("twofa.messages.trusted_device_removed"),
				level: "success",
			});
		},
		onError: (error) => {
			notifyMutationError(
				error,
				t("twofa.errors.remove_trusted_device"),
				showAsToast,
			);
		},
	});
}

/**
 * Update preferred 2FA method
 */
export function useSetPreferredMethod() {
	const queryClient = useQueryClient();
	const { showAsToast } = useApiMessages();
	const { t } = useTranslation();

	return useMutation<
		{ preferred_method: string; message: string },
		Error,
		TwoFactorMethod
	>({
		mutationFn: (method) => twoFactorServices.setPreferredMethod(method),
		onSuccess: (data) => {
			queryClient.invalidateQueries({ queryKey: twoFaKeys.status() });
			if (data?.message) {
				showToast({ message: data.message, level: "success" });
			} else {
				showToast({
					message: t("twofa.messages.default_method_updated"),
					level: "success",
				});
			}
		},
		onError: (error) => {
			notifyMutationError(
				error,
				t("twofa.errors.update_default_method"),
				showAsToast,
			);
		},
	});
}

/**
 * Remove a configured 2FA method
 */
export function useRemoveTwoFactorMethod() {
	const queryClient = useQueryClient();
	const { showAsToast } = useApiMessages();
	const { t } = useTranslation();

	return useMutation<TwoFactorMethodRemovalResponse, Error, TwoFactorMethod>({
		mutationFn: (method) => twoFactorServices.removeMethod(method),
		onSuccess: (data) => {
			queryClient.invalidateQueries({ queryKey: twoFaKeys.status() });
			if (data?.message) {
				showToast({ message: data.message, level: "success" });
			} else {
				showToast({
					message: t("twofa.messages.method_removed"),
					level: "success",
				});
			}
		},
		onError: (error) => {
			notifyMutationError(error, t("twofa.errors.remove_method"), showAsToast);
		},
	});
}
