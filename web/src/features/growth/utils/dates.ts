/** Growth dates are calendar days (`YYYY-MM-DD`); work with them in UTC so no timezone shifts them. */

const DAY_MS = 86_400_000;
/** The average month, for placing a point on an age axis. */
const DAYS_PER_MONTH = 365.25 / 12;

export function dayToUtcMs(day: string) {
	const [year, month, date] = day.split("-").map(Number);
	return Date.UTC(year, month - 1, date);
}

/** E.g. "Jun 1, 2025". */
export function formatDay(day: string | number, locale?: string) {
	const ms = typeof day === "number" ? day : dayToUtcMs(day);
	return new Date(ms).toLocaleDateString(locale, {
		timeZone: "UTC",
		year: "numeric",
		month: "short",
		day: "numeric",
	});
}

/** Fractional months from `birthdate` to `day`. */
export function ageInMonths(birthdate: string, day: string) {
	return (dayToUtcMs(day) - dayToUtcMs(birthdate)) / DAY_MS / DAYS_PER_MONTH;
}

/** Today on the viewer's own calendar, as `YYYY-MM-DD`. */
export function localToday(now = new Date()) {
	const month = String(now.getMonth() + 1).padStart(2, "0");
	const date = String(now.getDate()).padStart(2, "0");
	return `${now.getFullYear()}-${month}-${date}`;
}
