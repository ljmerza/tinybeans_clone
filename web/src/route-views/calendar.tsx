import { Layout, LoadingState } from "@/components";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import type { CircleMembershipSummary } from "@/features/circles";
import { useCircleMemberships } from "@/features/circles";
import {
	type CalendarMonthPayload,
	calendarMonthQueryOptions,
	currentMonthKey,
	useCalendarMonth,
} from "@/features/keeps";
import { PhotoCalendar } from "react-photo-calendar";
import "react-photo-calendar/styles.css";
import {
	type UseQueryResult,
	useQueries,
	useQueryClient,
} from "@tanstack/react-query";
import { getRouteApi, useNavigate } from "@tanstack/react-router";
import { useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

const route = getRouteApi("/calendar");

const ALL_CIRCLES = "all";

// Months scrolled past on mobile come back into view often; don't refetch
// each one every time it does.
const IN_VIEW_MONTH_STALE_TIME = 1000 * 60 * 5;

// Module-level so useQueries can reuse the combined array between renders.
function combineMonthEntries(results: UseQueryResult<CalendarMonthPayload>[]) {
	return results.flatMap((result) => result.data?.entries ?? []);
}

export function CalendarRouteView() {
	const { t } = useTranslation();
	const navigate = useNavigate();
	const search = route.useSearch();
	const month = search.month ?? currentMonthKey();
	const circleSlug = search.circle;

	const { data, isLoading, isFetching, error, refetch } = useCalendarMonth(
		month,
		circleSlug,
	);
	const { data: memberships } = useCircleMemberships();
	const queryClient = useQueryClient();

	// The mobile timeline shows several months at once; it reports the ones
	// on screen so their photos can be fetched alongside the current month.
	const [monthsInView, setMonthsInView] = useState<string[]>([]);
	const inViewEntries = useQueries({
		queries: monthsInView
			.filter((inViewMonth) => inViewMonth !== month)
			.map((inViewMonth) => ({
				...calendarMonthQueryOptions(inViewMonth, circleSlug),
				staleTime: IN_VIEW_MONTH_STALE_TIME,
				refetchOnMount: true,
			})),
		combine: combineMonthEntries,
	});
	const entries = useMemo(
		() => [...(data?.entries ?? []), ...inViewEntries],
		[data, inViewEntries],
	);

	// UTC days (yyyy-mm-dd) that have photos; only those open a day feed.
	const daysWithPhotos = useMemo(
		() =>
			new Set(
				entries.map((entry) =>
					new Date(entry.datetime).toISOString().slice(0, 10),
				),
			),
		[entries],
	);

	// Scrolling the timeline moves ?month= so going back from a day returns to
	// the month the user was on. The URL waits for that month's data: the
	// route loader would otherwise block and swap the timeline for its pending
	// screen. Only the latest scrolled-to month is written.
	const latestScrolledMonthRef = useRef<string | null>(null);
	const syncScrolledMonth = (nextMonthKey: string) => {
		latestScrolledMonthRef.current = nextMonthKey;
		queryClient
			.ensureQueryData(calendarMonthQueryOptions(nextMonthKey, circleSlug))
			.catch(() => undefined)
			.then(() => {
				if (latestScrolledMonthRef.current !== nextMonthKey) return;
				navigate({
					to: "/calendar",
					search: (previous) => ({ ...previous, month: nextMonthKey }),
					replace: true,
					resetScroll: false,
				});
			});
	};

	if (isLoading && !data) {
		return (
			<Layout.Loading
				showHeader={false}
				message={t("pages.calendar.loading")}
				spinnerSize="sm"
			/>
		);
	}

	if (error && !data) {
		return (
			<Layout.Error
				title={t("pages.calendar.error_title")}
				message={t("pages.calendar.error_message")}
				actionLabel={t("pages.calendar.retry")}
				onAction={() => refetch()}
			/>
		);
	}

	const circles = ((memberships ?? []) as CircleMembershipSummary[]).map(
		(membership) => membership.circle,
	);

	return (
		<Layout>
			{/* Layout's <main> already applies container-page padding. */}
			<div className="space-y-6">
				<header className="flex flex-wrap items-end justify-between gap-4">
					<div className="space-y-2">
						<h1 className="heading-2">{t("pages.calendar.title")}</h1>
						<p className="text-subtitle">{t("pages.calendar.subtitle")}</p>
						{/* Fixed-height slot so the indicator appearing/disappearing
						    does not push the calendar down. */}
						<div className="h-5">
							{isFetching ? (
								<LoadingState
									layout="inline"
									spinnerSize="sm"
									className="text-sm text-muted-foreground"
									message={t("pages.calendar.refreshing")}
								/>
							) : null}
						</div>
					</div>
					{circles.length > 1 ? (
						<Select
							value={circleSlug ?? ALL_CIRCLES}
							onValueChange={(value) =>
								navigate({
									to: "/calendar",
									search: {
										month,
										circle: value === ALL_CIRCLES ? undefined : value,
									},
								})
							}
						>
							<SelectTrigger className="w-56">
								<SelectValue placeholder={t("pages.calendar.select_circle")} />
							</SelectTrigger>
							<SelectContent>
								<SelectItem value={ALL_CIRCLES}>
									{t("pages.calendar.all_circles")}
								</SelectItem>
								{circles.map((circle) => (
									<SelectItem key={circle.slug} value={circle.slug}>
										{circle.name}
									</SelectItem>
								))}
							</SelectContent>
						</Select>
					) : null}
				</header>

				<PhotoCalendar
					monthKey={month}
					navigationMode="auto"
					maxMonthKey={currentMonthKey()}
					onMonthsInViewChange={setMonthsInView}
					onMonthChange={(nextMonthKey, { source }) => {
						if (source === "scroll") {
							syncScrolledMonth(nextMonthKey);
							return;
						}
						navigate({
							to: "/calendar",
							search: { month: nextMonthKey, circle: circleSlug },
						});
					}}
					onDaySelect={({ isoDate }) => {
						if (!daysWithPhotos.has(isoDate)) return;
						navigate({
							to: "/calendar/$date",
							params: { date: isoDate },
							search: { circle: circleSlug },
						});
					}}
					entries={entries}
					timeZone="UTC"
				/>
			</div>
		</Layout>
	);
}
