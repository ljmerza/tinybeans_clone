import type { ApiResponseWithMessages } from "@/types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { profileKeys } from "../api/queryKeys";
import {
	type NotificationPreferences,
	type UpdateNotificationPreferencesRequest,
	profileServices,
} from "../api/services";

function unwrap(
	response: ApiResponseWithMessages<NotificationPreferences>,
): NotificationPreferences {
	return (response.data ?? response) as NotificationPreferences;
}

/** Preferences in effect for a circle, or the user's defaults when `circleId` is null. */
export function useNotificationPreferences(circleId: number | null) {
	return useQuery({
		queryKey: profileKeys.notificationPreferences(circleId),
		queryFn: async () =>
			unwrap(await profileServices.getNotificationPreferences(circleId)),
	});
}

/**
 * Save preferences for the defaults (`circleId` null) or one circle. Passing
 * "reset" for a circle drops its override so the defaults apply again.
 */
export function useNotificationPreferencesMutation(circleId: number | null) {
	const queryClient = useQueryClient();

	return useMutation({
		mutationKey: profileKeys.mutations.updateNotificationPreferences(),
		mutationFn: async (
			change: UpdateNotificationPreferencesRequest | "reset",
		) =>
			unwrap(
				change === "reset" && circleId !== null
					? await profileServices.resetCircleNotificationPreferences(circleId)
					: await profileServices.updateNotificationPreferences(
							circleId,
							change as UpdateNotificationPreferencesRequest,
						),
			),
		onSuccess: (preferences) => {
			if (circleId === null) {
				// Circles without an override show the defaults, so refetch those.
				const defaultKey = profileKeys.notificationPreferences(null);
				void queryClient.invalidateQueries({
					queryKey: profileKeys.allNotificationPreferences(),
					predicate: (query) => query.queryKey.at(-1) !== defaultKey.at(-1),
				});
			}
			queryClient.setQueryData(
				profileKeys.notificationPreferences(circleId),
				preferences,
			);
		},
		meta: {
			toast: {
				error: { key: "common.error", status: 400 },
			},
		},
	});
}
