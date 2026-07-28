import { Layout } from "@/components";
import { requireAuth } from "@/features/auth";
import { calendarMonthQueryOptions, currentMonthKey } from "@/features/keeps";
import { CalendarRouteView } from "@/route-views/calendar";
import type { QueryClient } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

const MONTH_PATTERN = /^\d{4}-(0[1-9]|1[0-2])$/;

export const Route = createFileRoute("/calendar")({
	beforeLoad: requireAuth,
	validateSearch: (
		search: Record<string, unknown>,
	): { month?: string; circle?: string } => ({
		month:
			typeof search.month === "string" && MONTH_PATTERN.test(search.month)
				? search.month
				: undefined,
		circle: typeof search.circle === "string" ? search.circle : undefined,
	}),
	loaderDeps: ({ search }) => ({ month: search.month, circle: search.circle }),
	loader: async ({ context, deps }) => {
		const { queryClient } = context as unknown as {
			queryClient: QueryClient;
		};
		return queryClient.ensureQueryData({
			...calendarMonthQueryOptions(
				deps.month ?? currentMonthKey(),
				deps.circle,
			),
			// Return persisted/cached months immediately and refresh in the
			// background instead of blocking navigation on the network.
			revalidateIfStale: true,
		});
	},
	pendingComponent: CalendarPending,
	errorComponent: CalendarError,
	component: CalendarRouteView,
});

function CalendarPending() {
	const { t } = useTranslation();
	return <Layout.Loading message={t("pages.calendar.loading")} />;
}

function CalendarError({
	reset,
	error,
}: {
	reset?: () => void;
	error: unknown;
}) {
	const { t } = useTranslation();
	return (
		<Layout.Error
			title={t("pages.calendar.error_title")}
			message={t("pages.calendar.error_message")}
			actionLabel={t("pages.calendar.retry")}
			onAction={() => {
				console.error("Failed to load calendar", error);
				reset?.();
			}}
		/>
	);
}
