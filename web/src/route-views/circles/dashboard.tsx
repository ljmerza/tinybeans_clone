import { Layout } from "@/components/Layout";
import { LoadingState, EmptyState } from "@/components";
import { Button } from "@/components/ui/button";
import {
	CircleInvitationManager,
	useCircleMembers,
} from "@/features/circles";
import { Link } from "@tanstack/react-router";
import { useMemo } from "react";
import { useTranslation } from "react-i18next";

interface CircleDashboardProps {
	circleId: number | string;
}

export function CircleDashboard({ circleId }: CircleDashboardProps) {
	const { t } = useTranslation();
	const { data, isLoading, error, refetch, isFetching } =
		useCircleMembers(circleId);

	const members = data?.members ?? [];
	const adminCount = useMemo(
		() => members.filter((member) => member.role === "admin").length,
		[members],
	);
	const circle = data?.circle;

	if (isLoading && !data) {
		return (
			<Layout.Loading
				message={t("pages.circles.dashboard.loading")}
				spinnerSize="sm"
			/>
		);
	}

	if (error) {
		return (
			<Layout.Error
				title={t("pages.circles.dashboard.error_title")}
				message={t("pages.circles.dashboard.error_message")}
				actionLabel={t("pages.circles.dashboard.retry")}
				onAction={() => refetch()}
			/>
		);
	}

	return (
		<Layout>
			<div className="container-page space-y-8">
				<div className="space-y-4">
					<Button asChild variant="ghost" size="sm" className="px-0">
						<Link to="/circles">
							{t("pages.circles.dashboard.back_to_list")}
						</Link>
					</Button>

					<div className="space-y-2">
						<h1 className="heading-2">
							{circle?.name ?? t("pages.circles.dashboard.title_fallback")}
						</h1>
						<p className="text-subtitle">
							{t("pages.circles.dashboard.description", {
								count: circle?.member_count ?? members.length,
							})}
						</p>
						<div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
							<span>
								{t("pages.circles.dashboard.admin_count", { count: adminCount })}
							</span>
							<span>&middot;</span>
							<span>
								{t("pages.circles.dashboard.member_count", {
									count: members.length,
								})}
							</span>
							{isFetching ? (
								<>
									<span>&middot;</span>
									<LoadingState
										layout="inline"
										spinnerSize="sm"
										className="text-sm text-muted-foreground"
										message={t("pages.circles.dashboard.refreshing")}
									/>
								</>
							) : null}
						</div>
					</div>
				</div>

				<CircleInvitationManager circleId={circleId} />

				{members.length === 0 ? (
					<EmptyState
						title={t("pages.circles.dashboard.no_members_title")}
						description={t("pages.circles.dashboard.no_members_description")}
					/>
				) : null}
			</div>
		</Layout>
	);
}
