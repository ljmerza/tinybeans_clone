import type { QueryKey } from "@tanstack/react-query";
import { createQueryKeyFactory } from "@/lib/query/queryKeys";

const profileKeysFactory = createQueryKeyFactory(["user"] as const);

const mutationKey = <Parts extends QueryKey>(...parts: Parts) =>
	profileKeysFactory.tag("mutation", ...parts);

export const profileKeys = {
	all: () => profileKeysFactory.root(),
	profile: () => profileKeysFactory.tag("profile"),
	allNotificationPreferences: () =>
		profileKeysFactory.tag("notification-preferences"),
	notificationPreferences: (circleId: number | null) =>
		profileKeysFactory.tag("notification-preferences", circleId ?? "default"),
	notificationChannels: () => profileKeysFactory.tag("notification-channels"),
	mutation: mutationKey,
	mutations: {
		updateProfile: () => mutationKey("update-profile"),
		updateNotificationPreferences: () =>
			mutationKey("update-notification-preferences"),
		changePassword: () => mutationKey("change-password"),
		notificationPhone: () => mutationKey("notification-phone"),
		pushSubscription: () => mutationKey("push-subscription"),
	},
};

export const userKeys = profileKeys;
