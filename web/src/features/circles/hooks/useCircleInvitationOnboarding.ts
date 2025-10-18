import { authKeys } from "@/features/auth";
import { useApiMessages } from "@/i18n";
import type { ApiError, ApiResponseWithMessages } from "@/types";
import {
	type UseMutationResult,
	useMutation,
	useQueryClient,
} from "@tanstack/react-query";

import { circleKeys } from "../api/queryKeys";
import { circleServices } from "../api/services";
import type {
	CircleInvitationFinalizeResponse,
	CircleInvitationOnboardingStart,
} from "../types";
import {
	clearInvitation,
	loadInvitation,
	saveInvitation,
} from "../utils/invitationStorage";

export function useStartCircleInvitationOnboarding(): UseMutationResult<
	ApiResponseWithMessages<CircleInvitationOnboardingStart>,
	ApiError,
	string
> {
	const { showAsToast } = useApiMessages();

	return useMutation({
		mutationFn: (token: string) =>
			circleServices.startInvitationOnboarding(token),
		onSuccess: (response) => {
			const payload = (response.data ?? response) as CircleInvitationOnboardingStart;
			saveInvitation({
				onboardingToken: payload.onboarding_token,
				expiresInMinutes: payload.expires_in_minutes,
				invitation: payload.invitation,
			});
			if (response.messages?.length) {
				showAsToast(response.messages, 200);
			}
		},
		onError: (error) => {
			const status = error.status ?? 400;
			showAsToast(error.messages, status);
			clearInvitation();
		},
	});
}

export function loadStoredInvitation() {
	return loadInvitation();
}

export function useFinalizeCircleInvitation(): UseMutationResult<
	ApiResponseWithMessages<CircleInvitationFinalizeResponse>,
	ApiError,
	string
> {
	const queryClient = useQueryClient();
	const { showAsToast } = useApiMessages();

	return useMutation({
		mutationFn: (onboardingToken: string) =>
			circleServices.finalizeInvitation(onboardingToken),
		onSuccess: (response) => {
			clearInvitation();
			if (response.messages?.length) {
				showAsToast(response.messages, 201);
			}
			queryClient.invalidateQueries({ queryKey: circleKeys.onboarding() });
			queryClient.invalidateQueries({ queryKey: authKeys.session() });
		},
		onError: (error) => {
			clearInvitation();
			const status = error.status ?? 400;
			showAsToast(error.messages, status);
		},
	});
}
