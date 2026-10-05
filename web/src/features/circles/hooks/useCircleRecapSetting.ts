import { useMutation, useQueryClient } from "@tanstack/react-query";

import { circleKeys } from "../api/queryKeys";
import { circleServices } from "../api/services";
import type { CircleSummary } from "../types";
import type { CircleMembersPayload } from "./useCircleMemberships";

/**
 * Turns a circle's monthly recap album on or off (circle admins only; the API
 * refuses anyone else). Updates the circle on its settings page in place.
 */
export function useCircleRecapSettingMutation(circleId: number | string) {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: async (enabled: boolean) => {
			const response = await circleServices.updateCircle(circleId, {
				monthly_recap_enabled: enabled,
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
				error: { key: "pages.circles.dashboard.recap.save_failed" },
			},
		},
	});
}
