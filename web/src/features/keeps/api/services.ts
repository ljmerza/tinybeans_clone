import { apiClient as authApi } from "@/features/auth/api/authClient";
import type { ApiResponseWithMessages } from "@/types";
import type {
	AdjacentFeedDays,
	CalendarMonthPayload,
	FeedFilters,
	FeedKeep,
	FeedPage,
	KeepCommentRecord,
	KeepReactionRecord,
	PaginatedList,
} from "../types";

const KEEPS_BASE = "/keeps";

/** Upper bound for one keep's full comment thread in a single request. */
const COMMENT_THREAD_LIMIT = 200;

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
};
