import type { OnThisDayFrequency } from "@/features/keeps/utils/onThisDay";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { circleKeys } from "../api/queryKeys";
import { circleServices } from "../api/services";
import type { CircleSummary } from "../types";
import type { CircleMembersPayload } from "./useCircleMemberships";

/**
 * Sets how often a circle's "On this day" cards show in every member's home
 * feed (circle admins only; the API refuses anyone else). Updates the circle
 * on its settings page in place and refetches the feed's memories.
 */
export function useCircleOnThisDaySettingMutation(circleId: number | string) {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: async (frequency: OnThisDayFrequency) => {
			const response = await circleServices.updateCircle(circleId, {
				on_this_day_frequency: frequency,
			});
			return (response.data ?? response) as { circle: CircleSummary };
		},
		onSuccess: ({ circle }) => {
			queryClient.setQueryData<CircleMembersPayload>(
				circleKeys.members(circleId),
				(current) => (current ? { ...current, circle } : current),
			);
			void queryClient.invalidateQueries({ queryKey: circleKeys.list() });
			void queryClient.invalidateQueries({
				predicate: (query) => query.queryKey.includes("on-this-day"),
			});
		},
		meta: {
			toast: {
				error: { key: "pages.circles.dashboard.on_this_day.save_failed" },
			},
		},
	});
}
