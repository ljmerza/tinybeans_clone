import { apiClient as authApi } from "@/features/auth/api/authClient";

import type {
	ApproveSuggestionResponse,
	ListedSuggestionStatus,
	MilestoneSuggestion,
	MilestoneSuggestionPage,
} from "../types";

const suggestionsPath = (circleId: number | string) =>
	`/users/circles/${circleId}/milestone-suggestions/`;

/** Circle admins only; the API refuses anyone else. */
export const milestoneSuggestionServices = {
	/** Newest first, each with its post. */
	list(
		circleId: number | string,
		{ status, offset }: { status: ListedSuggestionStatus; offset?: number },
	) {
		const params = new URLSearchParams({ status });
		if (offset) params.set("offset", String(offset));
		return authApi.get<MilestoneSuggestionPage>(
			`${suggestionsPath(circleId)}?${params}`,
		);
	},

	/** Adds the post to the Milestones album; also undoes a dismiss. */
	approve(circleId: number | string, suggestionId: string) {
		return authApi.post<ApproveSuggestionResponse>(
			`${suggestionsPath(circleId)}${suggestionId}/approve/`,
		);
	},

	dismiss(circleId: number | string, suggestionId: string) {
		return authApi.post<{ suggestion: Omit<MilestoneSuggestion, "keep"> }>(
			`${suggestionsPath(circleId)}${suggestionId}/dismiss/`,
		);
	},
};
