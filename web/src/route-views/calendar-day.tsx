import { Layout, LoadingState } from "@/components";
import { Button } from "@/components/ui/button";
import {
	KeepFeedPost,
	useAdjacentFeedDays,
	useKeepFeed,
} from "@/features/keeps";
import { useSwipeNavigation } from "@/features/keeps/hooks/useSwipeNavigation";
import { Link, getRouteApi, useNavigate } from "@tanstack/react-router";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useCallback, useMemo } from "react";
import { useTranslation } from "react-i18next";
import "react-social-feed/styles.css";
import { VirtualFeed } from "react-social-feed/virtual";

const route = getRouteApi("/calendar_/$date");

/**
 * One calendar day's keeps as a feed, with arrows that jump to the nearest
 * earlier/later day that has photos.
 */
export function CalendarDayRouteView() {
	const { t, i18n } = useTranslation();
	const navigate = useNavigate();
	const { date } = route.useParams();
	const { circle: circleSlug } = route.useSearch();

	const {
		data,
		isLoading,
		error,
		refetch,
		fetchNextPage,
		hasNextPage,
		isFetchingNextPage,
		isFetchNextPageError,
	} = useKeepFeed({ date, circleSlug });
	const { data: adjacent } = useAdjacentFeedDays(date, circleSlug);

	const keeps = useMemo(
		() => data?.pages.flatMap((page) => page.results) ?? [],
		[data],
	);

	const loadMore = useCallback(() => {
		// Never restart a page that is already in flight.
		void fetchNextPage({ cancelRefetch: false });
	}, [fetchNextPage]);

	// Days are UTC, like the calendar's cells.
	const day = new Date(`${date}T00:00:00Z`);
	const dayLabel = new Intl.DateTimeFormat(i18n.language, {
		dateStyle: "full",
		timeZone: "UTC",
	}).format(day);
	const monthLabel = new Intl.DateTimeFormat(i18n.language, {
		month: "long",
		timeZone: "UTC",
	}).format(day);

	const goToDay = (nextDate: string) =>
		navigate({
			to: "/calendar/$date",
			params: { date: nextDate },
			search: { circle: circleSlug },
		});

	// Swipe left for the next day with photos, right for the previous one,
	// like the arrows beside the date.
	const swipeRef = useSwipeNavigation<HTMLDivElement>({
		onSwipeLeft: () => adjacent?.next && goToDay(adjacent.next),
		onSwipeRight: () => adjacent?.previous && goToDay(adjacent.previous),
	});

	const renderLoader = () => (
		<LoadingState
			layout="inline"
			spinnerSize="sm"
			className="justify-center py-6 text-sm text-muted-foreground"
			message={t("pages.feed.loading_more")}
		/>
	);

	const renderFeed = () => {
		if (isLoading && !data) {
			return (
				<LoadingState
					layout="inline"
					spinnerSize="sm"
					className="justify-center py-16 text-sm text-muted-foreground"
					message={t("pages.calendar_day.loading")}
				/>
			);
		}

		if (error && !data) {
			return (
				<div className="space-y-3 py-16 text-center">
					<h2 className="heading-3">{t("pages.calendar_day.error_title")}</h2>
					<p className="text-subtitle">{t("pages.feed.error_message")}</p>
					<Button variant="outline" size="sm" onClick={() => refetch()}>
						{t("pages.feed.retry")}
					</Button>
				</div>
			);
		}

		return (
			<VirtualFeed
				// Fresh measurements for each day.
				key={date}
				items={keeps}
				getItemKey={(keep) => keep.id}
				renderItem={(keep) => <KeepFeedPost keep={keep} />}
				// A failed page stops auto-paging; otherwise the list would
				// re-request it every time the in-flight flag drops.
				hasMore={hasNextPage && !isFetchNextPageError}
				isLoadingMore={isFetchingNextPage}
				onLoadMore={loadMore}
				renderLoader={renderLoader}
				renderEnd={() => {
					if (!isFetchNextPageError) return null;
					if (isFetchingNextPage) return renderLoader();
					return (
						<div className="space-y-3 py-6 text-center">
							<p className="text-sm text-muted-foreground">
								{t("pages.feed.load_more_error")}
							</p>
							<Button variant="outline" size="sm" onClick={loadMore}>
								{t("pages.feed.retry")}
							</Button>
						</div>
					);
				}}
				renderEmpty={() => (
					<div className="py-16 text-center">
						<h2 className="heading-3 mb-2">
							{t("pages.calendar_day.empty_title")}
						</h2>
						<p className="text-subtitle">
							{t("pages.calendar_day.empty_message")}
						</p>
					</div>
				)}
				aria-label={t("pages.calendar_day.aria_label", { date: dayLabel })}
			/>
		);
	};

	return (
		<Layout>
			{/* Layout's <main> already applies container-page padding. */}
			<div ref={swipeRef} className="space-y-6">
				<header className="mx-auto max-w-[var(--rsf-post-max-width)] space-y-2">
					<div className="flex items-center justify-between gap-2">
						<Button
							variant="ghost"
							size="icon"
							disabled={!adjacent?.previous}
							onClick={() => adjacent?.previous && goToDay(adjacent.previous)}
							aria-label={t("pages.calendar_day.previous_day")}
						>
							<ChevronLeft />
						</Button>
						<h1 className="heading-2 text-center">{dayLabel}</h1>
						<Button
							variant="ghost"
							size="icon"
							disabled={!adjacent?.next}
							onClick={() => adjacent?.next && goToDay(adjacent.next)}
							aria-label={t("pages.calendar_day.next_day")}
						>
							<ChevronRight />
						</Button>
					</div>
					<p className="text-center">
						<Link
							to="/calendar"
							search={{ month: date.slice(0, 7), circle: circleSlug }}
							className="text-sm underline underline-offset-4"
						>
							{t("pages.calendar_day.back_to_month", { month: monthLabel })}
						</Link>
					</p>
				</header>

				{renderFeed()}
			</div>
		</Layout>
	);
}
