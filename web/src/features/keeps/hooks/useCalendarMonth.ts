import type { ApiResponseWithMessages } from "@/types";
import { queryOptions, useQuery } from "@tanstack/react-query";

import { keepKeys } from "../api/queryKeys";
import { keepServices } from "../api/services";
import type { CalendarMonthPayload } from "../types";

function extractPayload(
	response: ApiResponseWithMessages<CalendarMonthPayload>,
): CalendarMonthPayload {
	if ("data" in response && response.data) {
		return response.data;
	}
	return response as unknown as CalendarMonthPayload;
}

/**
 * The user's current local month in the `YYYY-MM` key format the calendar API
 * expects. Local, not UTC: on the evening of the last day of a month in the
 * Americas, UTC has already rolled over and would open an empty next month.
 */
export function currentMonthKey(now: Date = new Date()) {
	const month = String(now.getMonth() + 1).padStart(2, "0");
	return `${now.getFullYear()}-${month}`;
}

/**
 * Shared query definition for one calendar month, used by both the route
 * loader and the hook so they always agree on key and caching behavior.
 *
 * Months are persisted to localStorage (see lib/query/persister.ts) and are
 * always refetched in the background: cached data renders instantly while a
 * fresh copy replaces it once the request completes.
 */
export function calendarMonthQueryOptions(month: string, circleSlug?: string) {
	return queryOptions({
		queryKey: keepKeys.calendarMonth(month, circleSlug),
		queryFn: async () =>
			extractPayload(await keepServices.getCalendarMonth(month, circleSlug)),
		staleTime: 0,
		refetchOnMount: "always" as const,
		// Keep browsed months in cache so month-to-month navigation is instant
		// and the persisted copy survives until the next visit.
		gcTime: 1000 * 60 * 60 * 24,
	});
}

export function useCalendarMonth(month: string, circleSlug?: string) {
	return useQuery(calendarMonthQueryOptions(month, circleSlug));
}
