import {
	type InfiniteData,
	type QueryClient,
	useInfiniteQuery,
	useMutation,
	useQuery,
	useQueryClient,
} from "@tanstack/react-query";

import { keepKeys } from "../api/queryKeys";
import { keepServices } from "../api/services";
import type {
	FeedComment,
	FeedFilters,
	FeedKeep,
	FeedPage,
	KeepCommentRecord,
} from "../types";

/**
 * Pull the opaque cursor out of DRF's absolute `next` URL.
 */
export function cursorFromNextUrl(next: string | null): string | undefined {
	if (!next) return undefined;
	return (
		new URL(next, "http://placeholder").searchParams.get("cursor") ?? undefined
	);
}

/**
 * Newest-first photo feed across every circle the user belongs to, or one
 * day's posts when `filters.date` is set.
 * Not persisted to localStorage: presigned media URLs expire after a day.
 */
export function useKeepFeed(filters: FeedFilters = {}) {
	const { date, circleSlug } = filters;
	return useInfiniteQuery({
		queryKey: date ? keepKeys.feedDay(date, circleSlug) : keepKeys.feed(),
		queryFn: ({ pageParam }) => keepServices.getFeed(pageParam, filters),
		initialPageParam: undefined as string | undefined,
		getNextPageParam: (lastPage: FeedPage) => cursorFromNextUrl(lastPage.next),
	});
}

/**
 * The nearest earlier/later days with posts, for the day view's arrows.
 */
export function useAdjacentFeedDays(date: string, circleSlug?: string) {
	return useQuery({
		queryKey: keepKeys.adjacentFeedDays(date, circleSlug),
		queryFn: () => keepServices.getAdjacentFeedDays(date, circleSlug),
	});
}

export function useFeedKeep(keepId: string) {
	return useQuery({
		queryKey: keepKeys.feedKeep(keepId),
		queryFn: () => keepServices.getFeedKeep(keepId),
	});
}

/**
 * A keep's full comment thread, fetched only once the user expands it.
 */
export function useKeepComments(keepId: string, enabled: boolean) {
	return useQuery({
		queryKey: keepKeys.comments(keepId),
		queryFn: async () => (await keepServices.getKeepComments(keepId)).results,
		enabled,
	});
}

/**
 * Apply `update` to a keep wherever it is cached: any loaded page of the home
 * or day feeds, and its single-keep query.
 */
function patchCachedKeep(
	queryClient: QueryClient,
	keepId: string,
	update: (keep: FeedKeep) => FeedKeep,
) {
	queryClient.setQueriesData<InfiniteData<FeedPage>>(
		{ queryKey: keepKeys.feed() },
		(data) =>
			data
				? {
						...data,
						pages: data.pages.map((page) => ({
							...page,
							results: page.results.map((keep) =>
								keep.id === keepId ? update(keep) : keep,
							),
						})),
					}
				: data,
	);
	queryClient.setQueryData<FeedKeep>(keepKeys.feedKeep(keepId), (keep) =>
		keep ? update(keep) : keep,
	);
}

/**
 * Like = the viewer has any reaction on the keep. Liking adds a `like`;
 * unliking removes whatever reaction the viewer has.
 *
 * The post UI flips optimistically and rolls back if this rejects, so the
 * cache is only written with the server's answer.
 */
export function useSetKeepLiked() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: async ({ keep, liked }: { keep: FeedKeep; liked: boolean }) => {
			if (liked) {
				const reaction = await keepServices.addReaction(keep.id);
				return {
					viewer_reaction: {
						id: reaction.id,
						reaction_type: reaction.reaction_type,
					},
					delta: 1,
				};
			}
			if (!keep.viewer_reaction) {
				// The like that created it hasn't come back yet.
				throw new Error("No reaction to remove yet");
			}
			await keepServices.removeReaction(keep.viewer_reaction.id);
			return { viewer_reaction: null, delta: -1 };
		},
		onSuccess: ({ viewer_reaction, delta }, { keep }) => {
			patchCachedKeep(queryClient, keep.id, (cached) => ({
				...cached,
				viewer_reaction,
				reaction_count: Math.max(0, cached.reaction_count + delta),
			}));
		},
	});
}

const toFeedComment = ({
	id,
	user,
	user_display_name,
	parent,
	comment,
	created_at,
}: KeepCommentRecord): FeedComment => ({
	id,
	user,
	user_display_name,
	parent,
	comment,
	created_at,
});

export function useAddKeepComment() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: ({
			keepId,
			text,
			parentId,
		}: {
			keepId: string;
			text: string;
			parentId?: number;
		}) => keepServices.addComment(keepId, text, parentId),
		meta: {
			toast: { error: { key: "pages.feed.comment_failed" } },
		},
		onSuccess: (record, { keepId }) => {
			const comment = toFeedComment(record);
			patchCachedKeep(queryClient, keepId, (cached) => ({
				...cached,
				comment_count: cached.comment_count + 1,
				recent_comments: [...cached.recent_comments, comment].slice(-2),
			}));
			queryClient.setQueryData<KeepCommentRecord[]>(
				keepKeys.comments(keepId),
				(thread) => (thread ? [...thread, record] : thread),
			);
		},
	});
}
