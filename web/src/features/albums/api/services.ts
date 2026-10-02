import { apiClient as authApi } from "@/features/auth/api/authClient";
import type { FeedPage } from "@/features/keeps/types";
import type {
	Album,
	AlbumPage,
	CreateAlbumInput,
	UpdateAlbumInput,
} from "../types";

const ALBUMS_BASE = "/albums";

export interface AlbumListParams {
	offset?: number;
	limit?: number;
	/** Only the albums of this post's circle, each with `has_keep`. */
	keep?: string;
	circleSlug?: string;
}

export const albumServices = {
	/** Most recently changed first. */
	list({ offset, limit, keep, circleSlug }: AlbumListParams = {}) {
		const params = new URLSearchParams();
		if (offset) params.set("offset", String(offset));
		if (limit) params.set("limit", String(limit));
		if (keep) params.set("keep", keep);
		if (circleSlug) params.set("circle_slug", circleSlug);
		const query = params.toString() ? `?${params}` : "";
		return authApi.get<AlbumPage>(`${ALBUMS_BASE}/${query}`);
	},

	get(albumId: string) {
		return authApi.get<Album>(`${ALBUMS_BASE}/${albumId}/`);
	},

	create(input: CreateAlbumInput) {
		return authApi.post<Album>(`${ALBUMS_BASE}/`, input);
	},

	/** Only its creator or a circle admin. */
	update(albumId: string, input: UpdateAlbumInput) {
		return authApi.patch<Album>(`${ALBUMS_BASE}/${albumId}/`, input);
	},

	/** Only its creator or a circle admin; the posts stay. */
	delete(albumId: string) {
		return authApi.delete<unknown>(`${ALBUMS_BASE}/${albumId}/`);
	},

	/** The album's posts in feed shape, oldest memory first. */
	getKeeps(albumId: string, cursor?: string) {
		const query = cursor ? `?${new URLSearchParams({ cursor })}` : "";
		return authApi.get<FeedPage>(`${ALBUMS_BASE}/${albumId}/keeps/${query}`);
	},

	/** Idempotent. */
	addKeep(albumId: string, keepId: string) {
		return authApi.post<{ in_album: true }>(
			`${ALBUMS_BASE}/${albumId}/keeps/${keepId}/`,
		);
	},

	/** Idempotent. */
	removeKeep(albumId: string, keepId: string) {
		return authApi.delete<unknown>(
			`${ALBUMS_BASE}/${albumId}/keeps/${keepId}/`,
		);
	},
};
