import {
	type InfiniteData,
	useInfiniteQuery,
	useMutation,
	useQuery,
	useQueryClient,
} from "@tanstack/react-query";

import { cursorFromNextUrl } from "@/features/keeps/hooks/useKeepFeed";
import type { FeedPage } from "@/features/keeps/types";
import i18n from "@/i18n/config";
import type { HttpError } from "@/lib/httpClient";
import { showToast } from "@/lib/toast";
import { albumKeys } from "../api/queryKeys";
import { albumServices } from "../api/services";
import type {
	Album,
	AlbumPage,
	CreateAlbumInput,
	UpdateAlbumInput,
} from "../types";

/** How many of a circle's albums the "Add to album" dialog lists. */
export const KEEP_ALBUMS_LIMIT = 200;

/**
 * Pull the offset out of DRF's absolute limit/offset `next` URL.
 */
export function offsetFromNextUrl(next: string | null): number | undefined {
	if (!next) return undefined;
	const offset = new URL(next, "http://placeholder").searchParams.get("offset");
	return offset ? Number(offset) : undefined;
}

const isNotFound = (error: unknown) => (error as HttpError).status === 404;

/**
 * Albums in every circle the viewer belongs to, most recently changed first.
 * Refetched on every visit: counts and covers change as posts are added
 * elsewhere.
 */
export function useAlbums() {
	return useInfiniteQuery({
		queryKey: albumKeys.list(),
		queryFn: ({ pageParam }) => albumServices.list({ offset: pageParam }),
		initialPageParam: 0,
		getNextPageParam: (lastPage: AlbumPage) => offsetFromNextUrl(lastPage.next),
		staleTime: 0,
	});
}

export function useAlbum(albumId: string) {
	return useQuery({
		queryKey: albumKeys.detail(albumId),
		queryFn: () => albumServices.get(albumId),
		staleTime: 0,
	});
}

/**
 * An album's posts, oldest memory first. Cached under the keeps feed key, so
 * likes, favorites, comments and deletes reach it; refetched on every visit.
 */
export function useAlbumKeeps(albumId: string) {
	return useInfiniteQuery({
		queryKey: albumKeys.feed(albumId),
		queryFn: ({ pageParam }) => albumServices.getKeeps(albumId, pageParam),
		initialPageParam: undefined as string | undefined,
		getNextPageParam: (lastPage: FeedPage) => cursorFromNextUrl(lastPage.next),
		staleTime: 0,
	});
}

/**
 * The albums of a post's circle, each flagged with whether the post is in it.
 */
export function useKeepAlbums(keepId: string) {
	return useQuery({
		queryKey: albumKeys.forKeep(keepId),
		queryFn: async () =>
			(await albumServices.list({ keep: keepId, limit: KEEP_ALBUMS_LIMIT }))
				.results,
		staleTime: 0,
	});
}

/**
 * Create an album; with `keep`, that post is its first. The new album joins
 * the post's "Add to album" list already checked.
 */
export function useCreateAlbum() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: (input: CreateAlbumInput) => albumServices.create(input),
		meta: {
			toast: { error: { key: "pages.albums.form.create_failed" } },
		},
		onSuccess: (album, { keep }) => {
			queryClient.setQueryData(albumKeys.detail(album.id), album);
			void queryClient.invalidateQueries({ queryKey: albumKeys.list() });
			if (keep) {
				queryClient.setQueryData<Album[]>(albumKeys.forKeep(keep), (albums) =>
					albums ? [{ ...album, has_keep: true }, ...albums] : albums,
				);
			}
		},
	});
}

/** Rename an album or change its description; only its creator or a circle admin. */
export function useUpdateAlbum() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: ({
			albumId,
			input,
		}: { albumId: string; input: UpdateAlbumInput }) =>
			albumServices.update(albumId, input),
		meta: {
			toast: { error: { key: "pages.albums.form.save_failed" } },
		},
		onSuccess: (album) => {
			queryClient.setQueryData(albumKeys.detail(album.id), album);
			void queryClient.invalidateQueries({ queryKey: albumKeys.list() });
			void queryClient.invalidateQueries({
				queryKey: albumKeys.forKeepAll(),
			});
		},
	});
}

/**
 * Pick an album's cover post, or pass null to go back to the default (the
 * album's first post); only circle admins.
 * The album's page and its card in the albums list show the new cover at once.
 */
export function useSetAlbumCover(albumId: string) {
	const queryClient = useQueryClient();

	return useMutation({
		mutationKey: albumKeys.setCover(albumId),
		mutationFn: (keepId: string | null) =>
			albumServices.update(albumId, { cover_keep: keepId }),
		meta: {
			toast: { error: { key: "pages.albums.cover.failed" } },
		},
		onSuccess: (album) => {
			queryClient.setQueryData(albumKeys.detail(album.id), album);
			queryClient.setQueryData<InfiniteData<AlbumPage>>(
				albumKeys.list(),
				(data) =>
					data && {
						...data,
						pages: data.pages.map((page) => ({
							...page,
							results: page.results.map((item) =>
								item.id === album.id ? album : item,
							),
						})),
					},
			);
			// Changing the cover also bumps the album to the top of the list.
			void queryClient.invalidateQueries({ queryKey: albumKeys.list() });
			void queryClient.invalidateQueries({
				queryKey: albumKeys.forKeepAll(),
			});
		},
		onError: () => {
			// E.g. the post left the album meanwhile; show what the album is now.
			void queryClient.invalidateQueries({
				queryKey: albumKeys.detail(albumId),
			});
		},
	});
}

/**
 * Delete an album (its posts stay); only its creator or a circle admin. A 404
 * means it is already gone, so that counts as deleted too.
 */
export function useDeleteAlbum() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: async (albumId: string) => {
			try {
				await albumServices.delete(albumId);
			} catch (error) {
				if (!isNotFound(error)) throw error;
			}
		},
		meta: {
			toast: {
				success: { key: "pages.albums.deleted" },
				error: { key: "pages.albums.delete_failed" },
			},
		},
		onSuccess: (_data, albumId) => {
			queryClient.removeQueries({ queryKey: albumKeys.detail(albumId) });
			queryClient.removeQueries({ queryKey: albumKeys.feed(albumId) });
			void queryClient.invalidateQueries({ queryKey: albumKeys.list() });
			void queryClient.invalidateQueries({
				queryKey: albumKeys.forKeepAll(),
			});
		},
	});
}

interface SetKeepInAlbumVariables {
	albumId: string;
	keepId: string;
	inAlbum: boolean;
}

/**
 * Add a post to an album or take it out; any circle member may.
 *
 * The post's album list flips optimistically and rolls back on failure. The
 * album's own post list is only marked stale, not refetched, so a post taken
 * out on the album's page stays (with its dialog open) until the next visit,
 * which keeps an accidental tap easy to undo.
 */
export function useSetKeepInAlbum() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: ({ albumId, keepId, inAlbum }: SetKeepInAlbumVariables) =>
			inAlbum
				? albumServices.addKeep(albumId, keepId)
				: albumServices.removeKeep(albumId, keepId),
		onMutate: async ({ albumId, keepId, inAlbum }) => {
			const key = albumKeys.forKeep(keepId);
			await queryClient.cancelQueries({ queryKey: key });
			const previous = queryClient.getQueryData<Album[]>(key);
			queryClient.setQueryData<Album[]>(key, (albums) =>
				albums?.map((album) =>
					album.id === albumId && album.has_keep !== inAlbum
						? {
								...album,
								has_keep: inAlbum,
								post_count: Math.max(0, album.post_count + (inAlbum ? 1 : -1)),
							}
						: album,
				),
			);
			return { previous };
		},
		onError: (error, { keepId }, context) => {
			queryClient.setQueryData(albumKeys.forKeep(keepId), context?.previous);
			if (isNotFound(error)) {
				void queryClient.invalidateQueries({
					queryKey: albumKeys.forKeep(keepId),
				});
				showToast({
					message: i18n.t("pages.albums.add.gone"),
					level: "info",
				});
				return;
			}
			showToast({
				message: i18n.t("pages.albums.add.toggle_failed"),
				level: "error",
			});
		},
		onSuccess: (_data, { albumId }) => {
			void queryClient.invalidateQueries({ queryKey: albumKeys.list() });
			void queryClient.invalidateQueries({
				queryKey: albumKeys.detail(albumId),
			});
			void queryClient.invalidateQueries({
				queryKey: albumKeys.feed(albumId),
				refetchType: "none",
			});
		},
	});
}
