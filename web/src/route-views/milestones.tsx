import { Layout, LoadingState } from "@/components";
import { Button } from "@/components/ui/button";
import {
	KeepFeedPost,
	useKeepChildren,
	useMilestoneKeeps,
} from "@/features/keeps";
import { Link, getRouteApi } from "@tanstack/react-router";
import { useCallback, useMemo } from "react";
import { useTranslation } from "react-i18next";
import "react-social-feed/styles.css";
import { VirtualFeed } from "react-social-feed/virtual";

const route = getRouteApi("/milestones");

/**
 * Milestone posts as a timeline, oldest first, optionally one child's. Opened
 * from a post's milestone badge. Children with milestones can be picked above
 * the list when there is more than one to choose between.
 */
export function MilestonesRouteView() {
	const { t } = useTranslation();
	const { child: childId } = route.useSearch();
	const {
		data,
		isLoading,
		error,
		refetch,
		fetchNextPage,
		hasNextPage,
		isFetchingNextPage,
		isFetchNextPageError,
	} = useMilestoneKeeps(childId);
	const { data: children } = useKeepChildren();

	const keeps = useMemo(
		() => data?.pages.flatMap((page) => page.results) ?? [],
		[data],
	);
	const withMilestones = (children ?? []).filter(
		(child) => child.milestone_count > 0 || child.id === childId,
	);
	const showPicker =
		withMilestones.length > 1 ||
		(childId !== undefined && withMilestones.length > 0);

	const loadMore = useCallback(() => {
		// Never restart a page that is already in flight.
		void fetchNextPage({ cancelRefetch: false });
	}, [fetchNextPage]);

	const renderLoader = () => (
		<LoadingState
			layout="inline"
			spinnerSize="sm"
			className="justify-center py-6 text-sm text-muted-foreground"
			message={t("pages.feed.loading_more")}
		/>
	);

	if (isLoading && !data) {
		return (
			<Layout.Loading
				showHeader={false}
				message={t("pages.milestones.loading")}
				spinnerSize="sm"
			/>
		);
	}

	if (error && !data) {
		return (
			<Layout.Error
				title={t("pages.milestones.error_title")}
				message={t("pages.milestones.error_message")}
				actionLabel={t("pages.feed.retry")}
				onAction={() => refetch()}
			/>
		);
	}

	return (
		<Layout>
			{/* Layout's <main> already applies container-page padding. */}
			<div className="space-y-6">
				{showPicker && (
					<nav
						aria-label={t("pages.milestones.children_label")}
						className="mx-auto flex max-w-[var(--rsf-post-max-width)] flex-wrap gap-2"
					>
						<Button
							asChild
							size="sm"
							variant={childId ? "outline" : "default"}
							className="rounded-full"
						>
							<Link
								to="/milestones"
								search={{}}
								aria-current={childId ? undefined : "page"}
							>
								{t("pages.milestones.everyone")}
							</Link>
						</Button>
						{withMilestones.map((child) => (
							<Button
								key={child.id}
								asChild
								size="sm"
								variant={child.id === childId ? "default" : "outline"}
								className="rounded-full"
							>
								<Link
									to="/milestones"
									search={{ child: child.id }}
									aria-current={child.id === childId ? "page" : undefined}
								>
									{child.display_name}
								</Link>
							</Button>
						))}
					</nav>
				)}

				<VirtualFeed
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
						if (!isFetchNextPageError) {
							return (
								<p className="py-6 text-center text-sm text-muted-foreground">
									{t("pages.milestones.end")}
								</p>
							);
						}
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
								{t("pages.milestones.empty_title")}
							</h2>
							<p className="text-subtitle">
								{t("pages.milestones.empty_message")}
							</p>
						</div>
					)}
					aria-label={t("pages.milestones.aria_label")}
				/>
			</div>
		</Layout>
	);
}
