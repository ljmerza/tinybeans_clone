import type { AuthRequestOptions } from "@/features/auth/api/authClient";
import { useApiMessages } from "@/i18n";
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
	const queryClient = useQueryClient();
	const { showAsToast } = useApiMessages();
	const shouldShowToast = !defaultRequestOptions?.suppressSuccessToast;

	return useMutation({
		mutationFn: (body: UpdateUserProfileVariables) =>
			profileServices.updateProfile(body, defaultRequestOptions),
		onSuccess: (response) => {
			queryClient.invalidateQueries({ queryKey: profileKeys.profile() });
			if (shouldShowToast && response.messages?.length) {
				showAsToast(response.messages, 200);
			}
		},
	});
}
