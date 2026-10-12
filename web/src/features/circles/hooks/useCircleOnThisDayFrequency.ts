import {
	type OnThisDayFrequency,
	toOnThisDayFrequency,
} from "@/features/keeps/utils/onThisDay";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { circleKeys } from "../api/queryKeys";
import { circleServices } from "../api/services";
import type { CircleMembershipSummary } from "../types";
import { useCircleMemberships } from "./useCircleMemberships";

/**
 * The viewer's own "On this day" frequency for one of their circles. Any
 * member can change theirs. The switch moves at once (it patches the cached
 * circle list) and goes back if the save fails; the home feed's memories are
 * refetched so the new spacing applies on the next visit.
 */
export function useCircleOnThisDayFrequency(circleId: number | string) {
	const queryClient = useQueryClient();
	const { data: memberships } = useCircleMemberships();
	const membership = memberships?.find(
		(item) => String(item.circle.id) === String(circleId),
	);
	const frequency = toOnThisDayFrequency(membership?.on_this_day_frequency);

	const setCached = (value: OnThisDayFrequency) => {
		queryClient.setQueryData<CircleMembershipSummary[]>(
			circleKeys.list(),
			(current) =>
				current?.map((item) =>
					String(item.circle.id) === String(circleId)
						? { ...item, on_this_day_frequency: value }
						: item,
				),
		);
	};

	const save = useMutation({
		mutationFn: (next: OnThisDayFrequency) =>
			circleServices.updateMyMembership(circleId, {
				on_this_day_frequency: next,
			}),
		onMutate: (next) => {
			const previous = frequency;
			setCached(next);
			return { previous };
		},
		onError: (_error, _next, context) => {
			if (context) setCached(context.previous);
		},
		onSuccess: () => {
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

	const setFrequency = (next: OnThisDayFrequency) => {
		if (next !== frequency) save.mutate(next);
	};

	return { frequency, setFrequency, isSaving: save.isPending };
}
