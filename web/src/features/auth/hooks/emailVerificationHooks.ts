import { useApiMessages } from "@/i18n";
import type { ApiError, ApiResponseWithMessages } from "@/types";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { authKeys } from "../api/queryKeys";
import { authServices } from "../api/services";

export function useResendVerificationMutation() {
	const { showAsToast } = useApiMessages();

	return useMutation<ApiResponseWithMessages, ApiError, string>({
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
	});
}

export function useVerifyEmailConfirm() {
	const queryClient = useQueryClient();

	return useMutation<ApiResponseWithMessages, ApiError, { token: string }>({
		mutationFn: (body) => authServices.confirmEmailVerification(body),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: authKeys.session() });
		},
		onError: (error) => {
			console.error("Email verification confirm error:", error);
		},
	});
}
