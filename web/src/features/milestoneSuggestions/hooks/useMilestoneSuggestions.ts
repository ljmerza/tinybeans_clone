import {
	type QueryClient,
	useInfiniteQuery,
	useMutation,
	useQuery,
	useQueryClient,
} from "@tanstack/react-query";

import { aiAssistKeys } from "@/features/aiAssist/api/queryKeys";
import { albumKeys } from "@/features/albums/api/queryKeys";
import { offsetFromNextUrl } from "@/features/albums/hooks/useAlbums";
import { keepKeys } from "@/features/keeps/api/queryKeys";
import { keepServices } from "@/features/keeps/api/services";
import type { FeedKeep } from "@/features/keeps/types";
import { milestoneSuggestionKeys } from "../api/queryKeys";
import { milestoneSuggestionServices } from "../api/services";
import type { ListedSuggestionStatus, MilestoneSuggestionPage } from "../types";

/** The circle's pending or dismissed suggestions, newest first (circle admins only). */
export function useMilestoneSuggestions(
	circleId: number | string,
	status: ListedSuggestionStatus,
	{ enabled = true }: { enabled?: boolean } = {},
) {
	return useInfiniteQuery({
		queryKey: milestoneSuggestionKeys.list(circleId, status),
		queryFn: ({ pageParam }) =>
			milestoneSuggestionServices.list(circleId, {
				status,
				offset: pageParam,
			}),
		initialPageParam: 0,
		getNextPageParam: (lastPage: MilestoneSuggestionPage) =>
			offsetFromNextUrl(lastPage.next),
		enabled,
		staleTime: 0,
	});
}

/** How many pending or dismissed suggestions the circle has (circle admins only). */
export function useMilestoneSuggestionCount(
	circleId: number | string,
	status: ListedSuggestionStatus,
	{ enabled = true }: { enabled?: boolean } = {},
) {
	return useQuery({
		queryKey: milestoneSuggestionKeys.count(circleId, status),
		queryFn: async () =>
			(await milestoneSuggestionServices.list(circleId, { status, limit: 1 }))
				.count,
		enabled,
		staleTime: 0,
	});
}

/**
 * A suggested post as the rest of the app has it cached. Seeded from the
 * suggestion list, then read from the post's single-keep query, which every
 * like, comment, edit and delete patches.
 */
export function useSuggestedKeep(keep: FeedKeep, loadedAt: number): FeedKeep {
	return useQuery({
		queryKey: keepKeys.feedKeep(keep.id),
		queryFn: () => keepServices.getFeedKeep(keep.id),
		initialData: keep,
		initialDataUpdatedAt: loadedAt,
	}).data;
}

/**
 * Refetch the circle's suggestion lists and counts, and the AI card's
 * "waiting for review" count.
 */
export function invalidateMilestoneSuggestions(
	queryClient: QueryClient,
	circleId: number | string,
) {
	void queryClient.invalidateQueries({
		queryKey: milestoneSuggestionKeys.circle(circleId),
	});
	void queryClient.invalidateQueries({
		queryKey: aiAssistKeys.settings(circleId),
	});
}

/**
 * Add a suggested post to the Milestones album (or undo a dismiss). The
 * album's page shows it on the next refetch.
 */
export function useApproveSuggestion(circleId: number | string) {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: (suggestionId: string) =>
			milestoneSuggestionServices.approve(circleId, suggestionId),
		meta: {
			toast: {
				success: { key: "pages.circles.milestone_suggestions.added" },
				error: { key: "pages.circles.milestone_suggestions.add_failed" },
			},
		},
		onSuccess: ({ album_id: albumId }) => {
			void queryClient.invalidateQueries({ queryKey: albumKeys.feed(albumId) });
			void queryClient.invalidateQueries({
				queryKey: albumKeys.detail(albumId),
			});
			void queryClient.invalidateQueries({ queryKey: albumKeys.list() });
		},
		onSettled: () => invalidateMilestoneSuggestions(queryClient, circleId),
	});
}

/** Turn a suggestion down; the post is not suggested again. */
export function useDismissSuggestion(circleId: number | string) {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: (suggestionId: string) =>
			milestoneSuggestionServices.dismiss(circleId, suggestionId),
		meta: {
			toast: {
				error: { key: "pages.circles.milestone_suggestions.dismiss_failed" },
			},
		},
		onSettled: () => invalidateMilestoneSuggestions(queryClient, circleId),
	});
}
