import type { Album } from "./types";

/** An album as the API returns it, for tests. */
export function makeAlbum(overrides: Partial<Album> = {}): Album {
	return {
		id: "aaaaaaaa-0000-0000-0000-000000000001",
		circle: { id: 7, name: "Family", slug: "family" },
		name: "Beach trip 2026",
		description: "",
		created_by: 1,
		created_by_display_name: "Leo",
		cover_keep: null,
		cover: null,
		post_count: 0,
		can_edit: true,
		has_keep: null,
		created_at: "2026-07-01T00:00:00Z",
		updated_at: "2026-07-01T00:00:00Z",
		...overrides,
	};
}

export const albumPage = (results: Album[], next: string | null = null) => ({
	count: results.length,
	next,
	previous: null,
	results,
});
