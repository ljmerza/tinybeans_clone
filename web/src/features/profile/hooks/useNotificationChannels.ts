import type { ApiResponseWithMessages } from "@/types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { profileKeys } from "../api/queryKeys";
import {
	type NotificationChannels,
	type PushSubscriptionPayload,
	profileServices,
} from "../api/services";

function unwrap(
	response: ApiResponseWithMessages<NotificationChannels>,
): NotificationChannels {
	return (response.data ?? response) as NotificationChannels;
}

/** Which channels the server offers, the user's SMS phone and push device count. */
export function useNotificationChannels() {
	return useQuery({
		queryKey: profileKeys.notificationChannels(),
		queryFn: async () =>
			unwrap(await profileServices.getNotificationChannels()),
	});
}

function useChannelsMutation<Variables>(
	mutationKey: readonly unknown[],
	request: (
		variables: Variables,
	) => Promise<ApiResponseWithMessages<NotificationChannels>>,
	afterSuccess?: (variables: Variables) => void,
) {
	const queryClient = useQueryClient();
	return useMutation({
		mutationKey,
		mutationFn: async (variables: Variables) =>
			unwrap(await request(variables)),
		onSuccess: (channels, variables) => {
			queryClient.setQueryData(profileKeys.notificationChannels(), channels);
			afterSuccess?.(variables);
		},
		meta: { toast: { useResponseMessages: true } },
	});
}

export type NotificationPhoneAction =
	| { action: "start"; phoneNumber: string }
	| { action: "verify"; code: string }
	| { action: "remove" };

/** Start, confirm or remove the phone notification texts go to. */
export function useNotificationPhoneMutation() {
	const queryClient = useQueryClient();
	return useChannelsMutation(
		profileKeys.mutations.notificationPhone(),
		(change: NotificationPhoneAction) => {
			if (change.action === "start") {
				return profileServices.startPhoneVerification(change.phoneNumber);
			}
			if (change.action === "verify") {
				return profileServices.verifyPhone(change.code);
			}
			return profileServices.removePhone();
		},
		(change) => {
			if (change.action === "remove") {
				// Removing the phone turns texts off in every scope.
				void queryClient.invalidateQueries({
					queryKey: profileKeys.allNotificationPreferences(),
				});
			}
		},
	);
}

/** Save or remove this browser's push subscription on the server. */
export function usePushSubscriptionMutation() {
	return useChannelsMutation(
		profileKeys.mutations.pushSubscription(),
		(change: { subscribe: PushSubscriptionPayload } | { remove: string }) =>
			"subscribe" in change
				? profileServices.savePushSubscription(change.subscribe)
				: profileServices.removePushSubscription(change.remove),
	);
}
