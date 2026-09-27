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

export interface KeepReactionRecord {
	id: number;
	keep: string;
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
