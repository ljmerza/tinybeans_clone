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
