import { useApiMessages } from "@/i18n";
import type { ApiError, ApiResponseWithMessages } from "@/types";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { authKeys } from "../api/queryKeys";
import { authServices } from "../api/services";

export function useResendVerificationMutation() {
	const { showAsToast } = useApiMessages();

	return useMutation<ApiResponseWithMessages, ApiError, string>({
		mutationKey: authKeys.mutations.resendVerification(),
		mutationFn: (identifier) =>
			authServices.resendVerificationEmail({ identifier }),
		onSuccess: (response) => {
			if (response.messages?.length) {
				showAsToast(response.messages, 202);
			}
		},
		onError: (error) => {
			console.error("Resend verification error:", error);
		},
		meta: {
			analyticsEvent: "auth:resend-verification",
			toast: {
				successKey: "common.success",
				errorKey: "auth.email_verification.error",
			},
		},
	});
}

export function useVerifyEmailConfirm() {
	const queryClient = useQueryClient();

	return useMutation<ApiResponseWithMessages, ApiError, { token: string }>({
		mutationKey: authKeys.mutations.verifyEmail(),
		mutationFn: (body) => authServices.confirmEmailVerification(body),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: authKeys.session() });
		},
		onError: (error) => {
			console.error("Email verification confirm error:", error);
		},
		meta: {
			analyticsEvent: "auth:verify-email",
			toast: {
				successKey: "auth.email_verification.success",
				errorKey: "auth.email_verification.error",
			},
		},
	});
}
