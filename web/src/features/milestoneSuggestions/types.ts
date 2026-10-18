import type { FeedKeep } from "@/features/keeps/types";

/**
 * Milestone suggestion types: posts in-app AI or an API token picked for a
 * circle's Milestones album.
 */

export type MilestoneSuggestionStatus =
	| "pending"
	| "approved"
	| "dismissed"
	| "not_milestone"
	| "auto_added";

/** Statuses the review list can show. */
export type ListedSuggestionStatus = "pending" | "dismissed";

export interface MilestoneSuggestion {
	id: string;
	status: MilestoneSuggestionStatus;
	/** `ai` = in-app AI; `agent` = an API token / MCP client. */
	source: "ai" | "agent";
	/** Untrusted text: render as plain text only. */
	label: string;
	/** Untrusted text: render as plain text only. Empty once dismissed. */
	reason: string;
	model_name: string;
	/** The suggesting token's "circ_xxxxxxx", for `agent` suggestions. */
	source_token_prefix: string;
	created_at: string;
	decided_at: string | null;
	/** The post in the feed's shape; null if the viewer can't see it. */
	keep: FeedKeep | null;
}

/** A limit/offset page; `next` is an absolute URL carrying `offset`. */
export interface MilestoneSuggestionPage {
	count: number;
	next: string | null;
	previous: string | null;
	results: MilestoneSuggestion[];
}

/** POST …/approve/ */
export interface ApproveSuggestionResponse {
	suggestion: Omit<MilestoneSuggestion, "keep">;
	/** The Milestones album the post went into. */
	album_id: string;
}
