import { createQueryKeyFactory } from "@/lib/query/queryKeys";

// Never persisted: only the ["keeps", "calendar"] prefix goes to localStorage.
const apiTokenKeysFactory = createQueryKeyFactory(["apiTokens"] as const);

export const apiTokenKeys = {
	all: () => apiTokenKeysFactory.root(),
	list: (circleId: number | string) =>
		apiTokenKeysFactory.tag("list", String(circleId)),
};
