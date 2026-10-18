import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { aiAssistKeys } from "../api/queryKeys";
import { aiAssistServices } from "../api/services";
import type { UpdateAiSettingsInput } from "../types";

/** The circle's in-app AI settings and scan status (circle admins only). */
export function useAiSettings(circleId: number | string) {
	return useQuery({
		queryKey: aiAssistKeys.settings(circleId),
		queryFn: () => aiAssistServices.getSettings(circleId),
	});
}

/** Turns in-app AI on (with the data-sharing acknowledgement) or off. */
export function useUpdateAiSettings(circleId: number | string) {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: (input: UpdateAiSettingsInput) =>
			aiAssistServices.updateSettings(circleId, input),
		meta: {
			toast: {
				useResponseMessages: true,
				error: { key: "pages.circles.dashboard.ai_assist.save_failed" },
			},
		},
		onSuccess: (settings) => {
			queryClient.setQueryData(aiAssistKeys.settings(circleId), settings);
		},
	});
}

/** Sends one made-up caption to the operator's model and reports the outcome code. */
export function useTestAiConnection(circleId: number | string) {
	return useMutation({
		mutationFn: () => aiAssistServices.testConnection(circleId),
		meta: {
			toast: {
				useResponseMessages: true,
				error: { key: "pages.circles.dashboard.ai_assist.test_failed" },
			},
		},
	});
}

/** Queues a milestone scan of the circle now. */
export function useScanMilestones(circleId: number | string) {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: () => aiAssistServices.scanNow(circleId),
		meta: {
			toast: {
				useResponseMessages: true,
				success: { key: "pages.circles.dashboard.ai_assist.scan_queued" },
				error: { key: "pages.circles.dashboard.ai_assist.scan_failed" },
			},
		},
		onSettled: () => {
			void queryClient.invalidateQueries({
				queryKey: aiAssistKeys.settings(circleId),
			});
		},
	});
}
