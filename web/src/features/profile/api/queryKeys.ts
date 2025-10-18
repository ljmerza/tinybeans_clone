import { createQueryKeyFactory } from "@/lib/query/queryKeys";

const profileKeysFactory = createQueryKeyFactory(["user"] as const);

export const profileKeys = {
	all: () => profileKeysFactory.root(),
	profile: () => profileKeysFactory.tag("profile"),
};

export const userKeys = profileKeys;
