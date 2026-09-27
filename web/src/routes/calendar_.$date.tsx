import { requireAuth } from "@/features/auth";
import { CalendarDayRouteView } from "@/route-views/calendar-day";
import { createFileRoute, redirect } from "@tanstack/react-router";

const DAY_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

/** Only real calendar dates, e.g. rejects 2026-02-30. */
function isValidDay(value: string) {
	if (!DAY_PATTERN.test(value)) return false;
	const date = new Date(`${value}T00:00:00Z`);
	return !Number.isNaN(date.getTime()) && date.toISOString().startsWith(value);
}

// `calendar_` opts out of nesting under /calendar, which renders no <Outlet>.
export const Route = createFileRoute("/calendar_/$date")({
	beforeLoad: async (ctx) => {
		await requireAuth(ctx);
		if (!isValidDay(ctx.params.date)) {
			throw redirect({
				to: "/calendar",
				search: { circle: ctx.search.circle },
			});
		}
	},
	validateSearch: (search: Record<string, unknown>): { circle?: string } => ({
		circle: typeof search.circle === "string" ? search.circle : undefined,
	}),
	component: CalendarDayRouteView,
});
