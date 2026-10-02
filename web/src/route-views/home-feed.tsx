import { Layout, LoadingState } from "@/components";
import { Button } from "@/components/ui/button";
import {
	type FeedRow,
	KeepFeedPost,
	NewPostDialog,
	OnThisDayCard,
	injectOnThisDay,
	localDate,
	onThisDaySeed,
	useKeepFeed,
	useOnThisDayKeeps,
	yearsAgo,
} from "@/features/keeps";
import { Plus } from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import "react-social-feed/styles.css";
import { VirtualFeed } from "react-social-feed/virtual";

/**
 * Home screen for signed-in users: every circle's photos, newest first, in a
 * virtualized infinite list, with "On this day" memories mixed in.
 */
export function HomeFeedView() {
	const { t } = useTranslation();
	const [composerOpen, setComposerOpen] = useState(false);
	const {
		data,
		isLoading,
		error,
		refetch,
		fetchNextPage,
		hasNextPage,
		isFetchingNextPage,
		isFetchNextPageError,
	} = useKeepFeed();

	const keeps = useMemo(
		() => data?.pages.flatMap((page) => page.results) ?? [],
		[data],
	);

	// Fixed for the visit: the viewer's local today, and a per-session seed so
	// the memory cards keep their places while scrolling and paging.
	const [today] = useState(() => localDate(new Date()));
	const [seed] = useState(onThisDaySeed);
	const { data: memoryData } = useOnThisDayKeeps(today);
	const rows = useMemo(
		() =>
			injectOnThisDay(
				keeps,
				memoryData?.pages.flatMap((page) => page.results) ?? [],
				{ seed, complete: data !== undefined && !hasNextPage },
			),
		[keeps, memoryData, seed, data, hasNextPage],
	);

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
				message={t("pages.feed.loading")}
				spinnerSize="sm"
			/>
		);
	}

	if (error && !data) {
		return (
			<Layout.Error
				title={t("pages.feed.error_title")}
				message={t("pages.feed.error_message")}
				actionLabel={t("pages.feed.retry")}
				onAction={() => refetch()}
			/>
		);
	}

	return (
		<Layout>
			{/* Layout's <main> already applies container-page padding. */}
			<div className="space-y-6">
				<div className="mx-auto flex max-w-[var(--rsf-post-max-width)] justify-end">
					<Button className="shrink-0" onClick={() => setComposerOpen(true)}>
						<Plus aria-hidden="true" />
						{t("pages.feed.new_post.open")}
					</Button>
				</div>
				{/* Mounted only while open, so the feed doesn't load circles up front. */}
				{composerOpen && <NewPostDialog open onOpenChange={setComposerOpen} />}

				<VirtualFeed
					items={rows}
					getItemKey={(row: FeedRow) =>
						row.kind === "post" ? row.keep.id : `on-this-day-${row.keep.id}`
					}
					renderItem={(row: FeedRow) =>
						row.kind === "post" ? (
							<KeepFeedPost keep={row.keep} />
						) : (
							<OnThisDayCard
								keep={row.keep}
								yearsAgo={yearsAgo(row.keep, today)}
							/>
						)
					}
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
									{t("pages.feed.end")}
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
							<h2 className="heading-3 mb-2">{t("pages.feed.empty_title")}</h2>
							<p className="text-subtitle">{t("pages.feed.empty_message")}</p>
						</div>
					)}
					aria-label={t("pages.feed.aria_label")}
				/>
			</div>
		</Layout>
	);
}
