import { createQueryKeyFactory } from "@/lib/query/queryKeys";

// Outside the persisted ["keeps", "calendar"] prefix, so never in localStorage.
const milestoneSuggestionKeysFactory = createQueryKeyFactory([
	"milestoneSuggestions",
] as const);

export const milestoneSuggestionKeys = {
	all: () => milestoneSuggestionKeysFactory.root(),
	circle: (circleId: number | string) =>
		milestoneSuggestionKeysFactory.tag("list", String(circleId)),
	list: (circleId: number | string, status: string) =>
		milestoneSuggestionKeysFactory.tag("list", String(circleId), status),
};
