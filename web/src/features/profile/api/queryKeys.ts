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
	mutation: mutationKey,
	mutations: {
		updateProfile: () => mutationKey("update-profile"),
		updateNotificationPreferences: () =>
			mutationKey("update-notification-preferences"),
	},
};

export const userKeys = profileKeys;
