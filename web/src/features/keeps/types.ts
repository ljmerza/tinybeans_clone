/**
 * Keeps feature types
 */

/**
 * A single calendar entry: one keep with the photos taken that day.
 */
export interface CalendarEntry {
	keep_id: string;
	datetime: string;
	photos: string[];
}

/**
 * Payload returned by GET /keeps/calendar/ for one month.
 */
export interface CalendarMonthPayload {
	month: string;
	circle_slug: string | null;
	entries: CalendarEntry[];
}

/**
 * A photo or video on a feed post. `width`/`height` are the original's
 * dimensions; the served rendition keeps that aspect ratio.
 */
export interface FeedMedia {
	id: number;
	media_type: "photo" | "video";
	url: string;
	/** The full-size file, for viewing a photo on its own. Missing in data cached before it was added. */
	original_url?: string;
	poster_url: string | null;
	width: number | null;
	height: number | null;
	caption: string;
}

export interface FeedComment {
	id: number;
	user: number;
	user_display_name: string;
	parent: number | null;
	comment: string;
	/** The viewer wrote it or admins its circle. */
	can_delete: boolean;
	created_at: string;
}

/**
 * One keep as returned by GET /keeps/feed/ and GET /keeps/feed/<id>/.
 */
export interface FeedKeep {
	id: string;
	circle: { id: number; name: string; slug: string };
	created_by: number;
	created_by_display_name: string;
	title: string;
	description: string;
	date_of_memory: string;
	created_at: string;
	media: FeedMedia[];
	reaction_count: number;
	comment_count: number;
	/** The viewer's own reaction, of any type. */
	viewer_reaction: { id: number; reaction_type: string } | null;
	/** Whether the viewer favorited it. Favorites are private to the viewer. */
	favorited: boolean;
	/** The viewer created it or admins its circle. */
	can_delete: boolean;
	/** The newest two comments, oldest first. */
	recent_comments: FeedComment[];
}

/**
 * A cursor-paginated feed page. `next` is an absolute URL carrying `cursor`.
 */
export interface FeedPage {
	next: string | null;
	previous: string | null;
	results: FeedKeep[];
}

/**
 * Narrows the feed to one UTC day (`YYYY-MM-DD`) and/or one circle.
 */
export interface FeedFilters {
	date?: string;
	circleSlug?: string;
}

/**
 * GET /keeps/feed/adjacent-days/: the closest days with posts either side of
 * `date`, or null when there are none.
 */
export interface AdjacentFeedDays {
	date: string;
	previous: string | null;
	next: string | null;
}

export interface KeepReactionRecord {
	id: number;
	keep: string;
	user: number;
	user_display_name: string;
	reaction_type: string;
	created_at: string;
}

/**
 * GET /keeps/feed/<id>/likers/: someone who reacted to a keep (any reaction
 * counts as a like), newest first.
 */
export interface KeepLiker {
	id: number;
	user: number;
	user_display_name: string;
	reaction_type: string;
	created_at: string;
}

export interface KeepCommentRecord extends FeedComment {
	keep: string;
	updated_at: string;
}

export interface PaginatedList<T> {
	count: number;
	next: string | null;
	previous: string | null;
	results: T[];
}

/**
 * POST /keeps/: the fields the web composer sends. `date_of_memory` is ISO.
 */
export interface CreateKeepInput {
	circle: number;
	keep_type: "note" | "media";
	title: string;
	description: string;
	date_of_memory: string;
}

export interface CreatedKeep extends CreateKeepInput {
	id: string;
}

export type MediaUploadStatus =
	| "pending"
	| "validating"
	| "processing"
	| "completed"
	| "failed";

/**
 * POST /keeps/upload/ and GET /keeps/upload/<id>/status/ (both wrapped in `data`).
 */
export interface MediaUploadRecord {
	id: string;
	keep: string;
	media_type: "photo" | "video";
	original_filename: string;
	status: MediaUploadStatus;
	error_message: string;
}
