import { apiClient as authApi } from "@/features/auth/api/authClient";
import type { ApiResponseWithMessages } from "@/types";
import type { CalendarMonthPayload } from "../types";

const KEEPS_BASE = "/keeps";

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
};
