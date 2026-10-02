import { useInfiniteQuery, useQuery } from "@tanstack/react-query";

import { keepKeys } from "../api/queryKeys";
import { keepServices } from "../api/services";
import type { FeedPage } from "../types";
import { cursorFromNextUrl } from "./useKeepFeed";

/**
 * Milestone posts across the viewer's circles, oldest first, or one child's
 * when `childId` is set. Cached under the feed key, so likes, favorites,
 * comments and deletes patch it like any feed post.
 */
export function useMilestoneKeeps(childId?: string) {
	return useInfiniteQuery({
		queryKey: keepKeys.feedMilestones(childId),
		queryFn: ({ pageParam }) => keepServices.getMilestones(pageParam, childId),
		initialPageParam: undefined as string | undefined,
		getNextPageParam: (lastPage: FeedPage) => cursorFromNextUrl(lastPage.next),
	});
}

/**
 * Children in the viewer's circles, for tagging and filtering milestones.
 */
export function useKeepChildren() {
	return useQuery({
		queryKey: keepKeys.children(),
		queryFn: () => keepServices.getChildren(),
	});
}
