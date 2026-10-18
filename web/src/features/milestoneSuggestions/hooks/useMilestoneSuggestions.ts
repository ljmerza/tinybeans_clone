import {
	useInfiniteQuery,
	useMutation,
	useQueryClient,
} from "@tanstack/react-query";

import { albumKeys } from "@/features/albums/api/queryKeys";
import { offsetFromNextUrl } from "@/features/albums/hooks/useAlbums";
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
		onSettled: () => {
			void queryClient.invalidateQueries({
				queryKey: milestoneSuggestionKeys.circle(circleId),
			});
		},
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
		onSettled: () => {
			void queryClient.invalidateQueries({
				queryKey: milestoneSuggestionKeys.circle(circleId),
			});
		},
	});
}
