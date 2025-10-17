import { authKeys } from "@/features/auth";
import { useApiMessages } from "@/i18n";
import type { ApiError, ApiResponseWithMessages } from "@/types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
	createCircle,
	fetchCircleOnboarding,
	skipCircleOnboarding,
} from "../api/onboardingClient";
import type { CircleOnboardingPayload, CircleSummary } from "../types";

export const circleKeys = {
	root: () => ["circles"] as const,
	onboarding: () => ["circles", "onboarding"] as const,
};

export function useCircleOnboardingQuery() {
	return useQuery({
		queryKey: circleKeys.onboarding(),
		queryFn: async () => {
			const response = await fetchCircleOnboarding();
			return (response.data ?? response) as CircleOnboardingPayload;
		},
	});
}

export function useSkipCircleOnboarding() {
	const queryClient = useQueryClient();
	const { showAsToast } = useApiMessages();

	return useMutation({
		mutationFn: skipCircleOnboarding,
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

export function useCreateCircleMutation() {
	const queryClient = useQueryClient();
	const { showAsToast } = useApiMessages();

	return useMutation({
		mutationFn: createCircle,
		onSuccess: (response: ApiResponseWithMessages<{ circle: CircleSummary }>) => {
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
