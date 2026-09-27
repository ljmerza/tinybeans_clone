import { Layout, LoadingState } from "@/components";
import { Button } from "@/components/ui/button";
import { KeepFeedPost, useKeepFeed } from "@/features/keeps";
import { useCallback, useMemo } from "react";
import { useTranslation } from "react-i18next";
import "react-social-feed/styles.css";
import { VirtualFeed } from "react-social-feed/virtual";

/**
 * Home screen for signed-in users: every circle's photos, newest first, in a
 * virtualized infinite list.
 */
export function HomeFeedView() {
	const { t } = useTranslation();
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
				<header className="mx-auto max-w-[var(--rsf-post-max-width)] space-y-2">
					<h1 className="heading-2">{t("pages.feed.title")}</h1>
					<p className="text-subtitle">{t("pages.feed.subtitle")}</p>
				</header>

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
