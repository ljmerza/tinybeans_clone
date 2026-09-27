import { createQueryKeyFactory } from "@/lib/query/queryKeys";

const keepKeysFactory = createQueryKeyFactory(["keeps"] as const);

export const keepKeys = {
	all: () => keepKeysFactory.root(),
	calendar: () => keepKeysFactory.tag("calendar"),
	calendarMonth: (month: string, circleSlug?: string) =>
		keepKeysFactory.tag("calendar", circleSlug ?? "all", month),
	feed: () => keepKeysFactory.tag("feed"),
	feedKeep: (keepId: string) => keepKeysFactory.tag("feed-keep", keepId),
	comments: (keepId: string) => keepKeysFactory.tag("comments", keepId),
};
