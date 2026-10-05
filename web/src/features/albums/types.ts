/**
 * Albums feature types
 */

/** The cover rendition: a photo, or a video's poster frame. */
export interface AlbumCover {
	keep_id: string;
	media_type: "photo" | "video";
	url: string;
}

/**
 * One album as returned by GET /albums/ and GET /albums/<id>/.
 */
export interface Album {
	id: string;
	circle: { id: number; name: string; slug: string };
	name: string;
	description: string;
	/** Null once the creator's account is deleted. */
	created_by: number | null;
	created_by_display_name: string | null;
	/** The chosen cover post, or null for the default (the first post). */
	cover_keep: string | null;
	cover: AlbumCover | null;
	/** Posts in the album the viewer can see. */
	post_count: number;
	/** The viewer created it or admins its circle, so may rename or delete it. */
	can_edit: boolean;
	/** With `?keep=`: whether that post is in the album; otherwise null. */
	has_keep: boolean | null;
	/** Monthly recap albums: first day (YYYY-MM-DD) of the month; otherwise null. */
	recap_month: string | null;
	created_at: string;
	updated_at: string;
}

/**
 * A limit/offset page of albums; `next` is an absolute URL carrying `offset`.
 */
export interface AlbumPage {
	count: number;
	next: string | null;
	previous: string | null;
	results: Album[];
}

/** POST /albums/: `keep` adds a first post from the same circle. */
export interface CreateAlbumInput {
	circle: number;
	name: string;
	description?: string;
	keep?: string;
}

/** PATCH /albums/<id>/ */
export interface UpdateAlbumInput {
	name?: string;
	description?: string;
	cover_keep?: string | null;
}
