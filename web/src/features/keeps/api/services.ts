import { apiClient as authApi } from "@/features/auth/api/authClient";
import type { ApiResponseWithMessages } from "@/types";
import type {
	AdjacentFeedDays,
	CalendarMonthPayload,
	CreateKeepInput,
	CreatedKeep,
	FeedFilters,
	FeedKeep,
	FeedPage,
	KeepCommentRecord,
	KeepLiker,
	KeepReactionRecord,
	MediaUploadRecord,
	OnThisDayPayload,
	PaginatedList,
} from "../types";

const KEEPS_BASE = "/keeps";

/** Upper bound for one keep's full comment thread in a single request. */
const COMMENT_THREAD_LIMIT = 200;

/** How many likers the "liked by" list loads. */
const LIKERS_LIMIT = 100;

export const keepServices = {
	getCalendarMonth(month: string, circleSlug?: string) {
		const params = new URLSearchParams({ month });
		if (circleSlug) {
			params.set("circle_slug", circleSlug);
		}
		return authApi.get<ApiResponseWithMessages<CalendarMonthPayload>>(
			`${KEEPS_BASE}/calendar/?${params.toString()}`,
		);
	},

	getFeed(cursor?: string, { date, circleSlug }: FeedFilters = {}) {
		const params = new URLSearchParams();
		if (cursor) params.set("cursor", cursor);
		if (date) params.set("date", date);
		if (circleSlug) params.set("circle_slug", circleSlug);
		const query = params.toString() ? `?${params}` : "";
		return authApi.get<FeedPage>(`${KEEPS_BASE}/feed/${query}`);
	},

	/** The viewer's favorites, most recently favorited first. */
	getFavorites(cursor?: string) {
		const query = cursor ? `?${new URLSearchParams({ cursor })}` : "";
		return authApi.get<FeedPage>(`${KEEPS_BASE}/feed/favorites/${query}`);
	},

	/** Idempotent; rejects with a 404 once the keep is deleted. */
	favoriteKeep(keepId: string) {
		return authApi.post<{ favorited: true }>(
			`${KEEPS_BASE}/feed/${keepId}/favorite/`,
		);
	},

	/** Idempotent; rejects with a 404 once the keep is deleted. */
	unfavoriteKeep(keepId: string) {
		return authApi.delete<unknown>(`${KEEPS_BASE}/feed/${keepId}/favorite/`);
	},

	/** Earlier years' posts from `date` (the viewer's local today)'s month and day. */
	getOnThisDay(date: string) {
		const params = new URLSearchParams({ date });
		return authApi.get<OnThisDayPayload>(
			`${KEEPS_BASE}/feed/on-this-day/?${params}`,
		);
	},

	getAdjacentFeedDays(date: string, circleSlug?: string) {
		const params = new URLSearchParams({ date });
		if (circleSlug) params.set("circle_slug", circleSlug);
		return authApi.get<AdjacentFeedDays>(
			`${KEEPS_BASE}/feed/adjacent-days/?${params}`,
		);
	},

	getFeedKeep(keepId: string) {
		return authApi.get<FeedKeep>(`${KEEPS_BASE}/feed/${keepId}/`);
	},

	getKeepComments(keepId: string) {
		const params = new URLSearchParams({
			keep: keepId,
			limit: String(COMMENT_THREAD_LIMIT),
		});
		return authApi.get<PaginatedList<KeepCommentRecord>>(
			`${KEEPS_BASE}/comments/?${params}`,
		);
	},

	/** Newest first; `count` is the total when it exceeds the limit. */
	getKeepLikers(keepId: string) {
		const params = new URLSearchParams({ limit: String(LIKERS_LIMIT) });
		return authApi.get<PaginatedList<KeepLiker>>(
			`${KEEPS_BASE}/feed/${keepId}/likers/?${params}`,
		);
	},

	addReaction(keepId: string, reactionType = "like") {
		return authApi.post<KeepReactionRecord>(`${KEEPS_BASE}/reactions/`, {
			keep: keepId,
			reaction_type: reactionType,
		});
	},

	removeReaction(reactionId: number) {
		return authApi.delete<unknown>(`${KEEPS_BASE}/reactions/${reactionId}/`);
	},

	/** `parent` is the comment being replied to; omit it for a top-level comment. */
	addComment(keepId: string, comment: string, parent?: number) {
		return authApi.post<KeepCommentRecord>(`${KEEPS_BASE}/comments/`, {
			keep: keepId,
			comment,
			...(parent !== undefined && { parent }),
		});
	},

	createKeep(input: CreateKeepInput) {
		return authApi.post<CreatedKeep>(`${KEEPS_BASE}/`, input);
	},

	deleteKeep(keepId: string) {
		return authApi.delete<unknown>(`${KEEPS_BASE}/${keepId}/`);
	},

	getUploadStatus(uploadId: string) {
		return authApi.get<ApiResponseWithMessages<MediaUploadRecord>>(
			`${KEEPS_BASE}/upload/${uploadId}/status/`,
		);
	},

	/** Deleting a top-level comment also deletes its replies. */
	deleteComment(commentId: number) {
		return authApi.delete<unknown>(`${KEEPS_BASE}/comments/${commentId}/`);
	},
};
