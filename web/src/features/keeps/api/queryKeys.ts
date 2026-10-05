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
	/** Posts a person is tagged on; nested under `feed` so cache patches reach it. */
	feedPerson: (personId: string) =>
		keepKeysFactory.tag("feed", "person", personId),
	/** Earlier years' posts from `date`'s month and day; nested under `feed` so cache patches reach it. */
	feedOnThisDay: (date: string) =>
		keepKeysFactory.tag("feed", "on-this-day", date),
	adjacentFeedDays: (date: string, circleSlug?: string) =>
		keepKeysFactory.tag("adjacent-feed-days", circleSlug ?? "all", date),
	/** Every cached adjacent-days lookup, e.g. once a post moves to another day. */
	adjacentFeedDaysAll: () => keepKeysFactory.tag("adjacent-feed-days"),
	feedKeep: (keepId: string) => keepKeysFactory.tag("feed-keep", keepId),
	comments: (keepId: string) => keepKeysFactory.tag("comments", keepId),
	likers: (keepId: string) => keepKeysFactory.tag("likers", keepId),
	/** Everyone who can be tagged on a circle's posts. */
	circlePeople: (circleId: number) =>
		keepKeysFactory.tag("circle-people", circleId),
	person: (personId: string) => keepKeysFactory.tag("person", personId),
	uploadLimits: () => keepKeysFactory.tag("upload-limits"),
};
