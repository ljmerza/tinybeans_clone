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
import { currentMonthKey, useCalendarMonth } from "@/features/keeps";
import { PhotoCalendar } from "@/vendor/photo-calendar";
import { getRouteApi, useNavigate } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

const route = getRouteApi("/calendar");

const ALL_CIRCLES = "all";

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
			<div className="container-page space-y-6">
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
					onMonthChange={(nextMonthKey) =>
						navigate({
							to: "/calendar",
							search: { month: nextMonthKey, circle: circleSlug },
						})
					}
					entries={data?.entries ?? []}
					timeZone="UTC"
				/>
			</div>
		</Layout>
	);
}
