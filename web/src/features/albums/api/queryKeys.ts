import { keepKeys } from "@/features/keeps/api/queryKeys";
import { createQueryKeyFactory } from "@/lib/query/queryKeys";

const albumKeysFactory = createQueryKeyFactory(["albums"] as const);

export const albumKeys = {
	all: () => albumKeysFactory.root(),
	list: () => albumKeysFactory.tag("list"),
	forKeepAll: () => albumKeysFactory.tag("for-keep"),
	/** A post's circle's albums, flagged with whether the post is in each. */
	forKeep: (keepId: string) => albumKeysFactory.tag("for-keep", keepId),
	detail: (albumId: string) => albumKeysFactory.tag("detail", albumId),
	/**
	 * An album's posts. Nested under the keeps feed key so likes, favorites,
	 * comments and deletes patch it like any other feed.
	 */
	feed: (albumId: string) => [...keepKeys.feed(), "album", albumId] as const,
};
