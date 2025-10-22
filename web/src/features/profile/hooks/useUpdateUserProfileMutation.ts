import { authKeys } from "@/features/auth/api/queryKeys";
import type { AuthRequestOptions } from "@/features/auth/api/authClient";
import type { ApiError, ApiResponseWithMessages } from "@/types";
import {
	type UseMutationResult,
	useMutation,
	useQueryClient,
} from "@tanstack/react-query";
import { profileKeys } from "../api/queryKeys";
import {
	type UpdateUserProfileRequest,
	type UserProfileResponse,
	profileServices,
} from "../api/services";

type UpdateUserProfileVariables = UpdateUserProfileRequest;
type UpdateUserProfileResult = ApiResponseWithMessages<UserProfileResponse>;

export function useUpdateUserProfileMutation(
	defaultRequestOptions?: AuthRequestOptions,
): UseMutationResult<
	UpdateUserProfileResult,
	ApiError,
	UpdateUserProfileVariables
> {
	const mutationKey = profileKeys.mutations.updateProfile();
	const queryClient = useQueryClient();
	const shouldShowToast = !defaultRequestOptions?.suppressSuccessToast;

	return useMutation({
		mutationKey,
		mutationFn: (body: UpdateUserProfileVariables) =>
			profileServices.updateProfile(body, defaultRequestOptions),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: profileKeys.profile() });
			queryClient.invalidateQueries({ queryKey: authKeys.session() });
		},
		meta: {
			analyticsEvent: "profile:update",
			toast: {
				useResponseMessages: true,
				success: {
					key: "common.success",
					status: 200,
					suppress: !shouldShowToast,
				},
				error: {
					key: "common.error",
					status: 400,
				},
			},
		},
	});
}
