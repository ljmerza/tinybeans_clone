import { createQueryKeyFactory } from "@/lib/query/queryKeys";

const keepKeysFactory = createQueryKeyFactory(["keeps"] as const);

export const keepKeys = {
	all: () => keepKeysFactory.root(),
	calendar: () => keepKeysFactory.tag("calendar"),
	calendarMonth: (month: string, circleSlug?: string) =>
		keepKeysFactory.tag("calendar", circleSlug ?? "all", month),
	feed: () => keepKeysFactory.tag("feed"),
	/** Nested under `feed` so cache patches reach every feed variant. */
	feedDay: (date: string, circleSlug?: string) =>
		keepKeysFactory.tag("feed", "day", circleSlug ?? "all", date),
	/** The viewer's favorites; nested under `feed` so cache patches reach it. */
	feedFavorites: () => keepKeysFactory.tag("feed", "favorites"),
	/** Earlier years' posts from `date`'s month and day; nested under `feed` so cache patches reach it. */
	feedOnThisDay: (date: string) =>
		keepKeysFactory.tag("feed", "on-this-day", date),
	adjacentFeedDays: (date: string, circleSlug?: string) =>
		keepKeysFactory.tag("adjacent-feed-days", circleSlug ?? "all", date),
	feedKeep: (keepId: string) => keepKeysFactory.tag("feed-keep", keepId),
	comments: (keepId: string) => keepKeysFactory.tag("comments", keepId),
	likers: (keepId: string) => keepKeysFactory.tag("likers", keepId),
};
