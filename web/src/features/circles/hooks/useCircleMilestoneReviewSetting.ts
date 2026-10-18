import { useMutation, useQueryClient } from "@tanstack/react-query";

import { circleKeys } from "../api/queryKeys";
import { circleServices } from "../api/services";
import type { CircleSummary } from "../types";
import type { CircleMembersPayload } from "./useCircleMemberships";

/**
 * Turns review of AI and API token milestone picks on or off (circle admins
 * only; the API refuses anyone else). Updates the circle on its settings page
 * in place.
 */
export function useCircleMilestoneReviewSettingMutation(
	circleId: number | string,
) {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: async (enabled: boolean) => {
			const response = await circleServices.updateCircle(circleId, {
				review_ai_milestones: enabled,
			});
			return (response.data ?? response) as { circle: CircleSummary };
		},
		onSuccess: ({ circle }) => {
			queryClient.setQueryData<CircleMembersPayload>(
				circleKeys.members(circleId),
				(current) => (current ? { ...current, circle } : current),
			);
			void queryClient.invalidateQueries({ queryKey: circleKeys.list() });
		},
		meta: {
			toast: {
				error: {
					key: "pages.circles.dashboard.milestone_review.save_failed",
				},
			},
		},
	});
}
