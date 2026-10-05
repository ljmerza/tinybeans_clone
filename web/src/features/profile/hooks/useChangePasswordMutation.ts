import { setAccessToken } from "@/features/auth/store/authStore";
import type { ApiError, ApiResponseWithMessages } from "@/types";
import { type UseMutationResult, useMutation } from "@tanstack/react-query";
import { profileKeys } from "../api/queryKeys";
import {
	type ChangePasswordRequest,
	type ChangePasswordResponse,
	profileServices,
} from "../api/services";

type ChangePasswordResult = ApiResponseWithMessages<ChangePasswordResponse>;

export function useChangePasswordMutation(): UseMutationResult<
	ChangePasswordResult,
	ApiError,
	ChangePasswordRequest
> {
	return useMutation({
		mutationKey: profileKeys.mutations.changePassword(),
		mutationFn: (body: ChangePasswordRequest) =>
			profileServices.changePassword(body),
		onSuccess: (response) => {
			// Every refresh token was revoked and the response set a new refresh
			// cookie; keep this tab signed in with the access token issued with it.
			const access = response.data?.tokens?.access;
			if (access) {
				setAccessToken(access);
			}
		},
		meta: {
			analyticsEvent: "profile:change-password",
			toast: {
				success: { key: "profile.password.changed", status: 200 },
				// Errors are shown inline next to the fields.
				error: { suppress: true },
			},
		},
	});
}
