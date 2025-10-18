import { authKeys } from "@/features/auth";
import { useApiMessages } from "@/i18n";
import type { ApiError, ApiResponseWithMessages } from "@/types";
import {
	type UseMutationResult,
	type UseQueryResult,
	useMutation,
	useQuery,
	useQueryClient,
} from "@tanstack/react-query";

import { circleKeys } from "../api/queryKeys";
import { circleServices } from "../api/services";
import type { CircleOnboardingPayload, CircleSummary } from "../types";

export function useCircleOnboardingQuery(): UseQueryResult<CircleOnboardingPayload> {
	return useQuery({
		queryKey: circleKeys.onboarding(),
		queryFn: async () => {
			const response = await circleServices.getOnboarding();
			return (response.data ?? response) as CircleOnboardingPayload;
		},
	});
}

export function useSkipCircleOnboarding(): UseMutationResult<
	ApiResponseWithMessages<CircleOnboardingPayload>,
	ApiError,
	void
> {
	const queryClient = useQueryClient();
	const { showAsToast } = useApiMessages();

	return useMutation({
		mutationFn: () => circleServices.skipOnboarding(),
		onSuccess: (response: ApiResponseWithMessages<CircleOnboardingPayload>) => {
			const payload = (response.data ?? response) as CircleOnboardingPayload;
			queryClient.setQueryData(circleKeys.onboarding(), payload);
			queryClient.invalidateQueries({ queryKey: authKeys.session() });
			if (response.messages?.length) {
				showAsToast(response.messages, 200);
			}
		},
		onError: (error: ApiError) => {
			console.error("Skip onboarding error:", error);
		},
	});
}

export function useCreateCircleMutation(): UseMutationResult<
	ApiResponseWithMessages<{ circle: CircleSummary }>,
	ApiError,
	{ name: string }
> {
	const queryClient = useQueryClient();
	const { showAsToast } = useApiMessages();

	return useMutation({
		mutationFn: circleServices.createCircle,
		onSuccess: (
			response: ApiResponseWithMessages<{ circle: CircleSummary }>,
		) => {
			queryClient.invalidateQueries({ queryKey: circleKeys.onboarding() });
			queryClient.invalidateQueries({ queryKey: authKeys.session() });
			if (response.messages?.length) {
				showAsToast(response.messages, 201);
			}
		},
		onError: (error: ApiError) => {
			console.error("Create circle error:", error);
		},
	});
}
