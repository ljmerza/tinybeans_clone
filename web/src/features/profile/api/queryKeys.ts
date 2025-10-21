import type { QueryKey } from "@tanstack/react-query";
import { createQueryKeyFactory } from "@/lib/query/queryKeys";

const profileKeysFactory = createQueryKeyFactory(["user"] as const);

const mutationKey = <Parts extends QueryKey>(...parts: Parts) =>
	profileKeysFactory.tag("mutation", ...parts);

export const profileKeys = {
	all: () => profileKeysFactory.root(),
	profile: () => profileKeysFactory.tag("profile"),
	mutation: mutationKey,
	mutations: {
		updateProfile: () => mutationKey("update-profile"),
	},
};

export const userKeys = profileKeys;
