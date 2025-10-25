import type { ApiError, ApiResponseWithMessages } from "@/types";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { authKeys } from "../api/queryKeys";
import { authServices } from "../api/services";

export function useResendVerificationMutation() {
	return useMutation<ApiResponseWithMessages, ApiError, void>({
		mutationKey: authKeys.mutations.resendVerification(),
		mutationFn: () => authServices.resendVerificationEmail(),
		onError: (error) => {
			console.error("Resend verification error:", error);
		},
		meta: {
			analyticsEvent: "auth:resend-verification",
			toast: {
				useResponseMessages: true,
				success: {
					key: "auth.verify_email_required.resend_success",
					status: 202,
				},
				error: {
					key: "auth.verify_email_required.resend_error",
					status: 400,
				},
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
				useResponseMessages: true,
				success: {
					key: "auth.email_verification.success",
					status: 200,
				},
				error: {
					key: "auth.email_verification.error",
					status: 400,
				},
			},
		},
	});
}
