import { Layout, LoadingState } from "@/components";
import { Button } from "@/components/ui/button";
import { PersonInsights } from "@/features/growth";
import { KeepFeedPost, usePerson, usePersonKeeps } from "@/features/keeps";
import { Link, getRouteApi } from "@tanstack/react-router";
import { ArrowLeft } from "lucide-react";
import { useCallback, useLayoutEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import "react-social-feed/styles.css";
import { VirtualFeed } from "react-social-feed/virtual";

const route = getRouteApi("/people/$personId");

/**
 * The feed's distance from the top of the page, for its window virtualizer.
 * The feed measures this itself only once, but the stats and growth sections
 * right above it grow as they load, so it is re-measured whenever they resize.
 */
function useFeedTop(above: HTMLElement | null) {
	const [top, setTop] = useState<number>();
	useLayoutEffect(() => {
		if (!above) return;
		const measure = () => {
			// The feed is the next element after the sections.
			const feed = above.nextElementSibling;
			if (feed) setTop(feed.getBoundingClientRect().top + window.scrollY);
		};
		measure();
		window.addEventListener("resize", measure);
		const observer =
			typeof ResizeObserver === "undefined"
				? null
				: new ResizeObserver(measure);
		observer?.observe(above);
		return () => {
			window.removeEventListener("resize", measure);
			observer?.disconnect();
		};
	}, [above]);
	return top;
}

/**
 * The home feed filtered to one person: every post they are tagged on, newest
 * memory first, under a compact line with their name and circle.
 */
export function PersonRouteView() {
	const { t } = useTranslation();
	const { personId } = route.useParams();
	const person = usePerson(personId);
	const {
		data,
		error,
		refetch,
		fetchNextPage,
		hasNextPage,
		isFetchingNextPage,
		isFetchNextPageError,
	} = usePersonKeeps(personId);

	const [insightsElement, setInsightsElement] = useState<HTMLElement | null>(
		null,
	);
	const feedTop = useFeedTop(insightsElement);

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

	if (person.isLoading || (!data && !error)) {
		return (
			<Layout.Loading
				showHeader={false}
				message={t("pages.people.page.loading")}
				spinnerSize="sm"
			/>
		);
	}

	const backLink = (
		<Link
			to="/"
			aria-label={t("pages.people.page.back")}
			title={t("pages.people.page.back")}
			className="-ml-2 inline-flex size-9 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
		>
			<ArrowLeft className="size-5" aria-hidden="true" />
		</Link>
	);

	if (!person.data) {
		return (
			<Layout>
				<div className="mx-auto max-w-[var(--rsf-post-max-width)] py-16 text-center">
					<h1 className="heading-3 mb-2">
						{t("pages.people.page.not_found_title")}
					</h1>
					<p className="text-subtitle mb-6">
						{t("pages.people.page.not_found_message")}
					</p>
					<Link to="/" className="text-sm underline underline-offset-4">
						{t("pages.people.page.back")}
					</Link>
				</div>
			</Layout>
		);
	}

	const { name, circle } = person.data;

	return (
		<Layout>
			{/* Layout's <main> already applies container-page padding. */}
			<div className="space-y-4">
				<div className="mx-auto flex max-w-[var(--rsf-post-max-width)] items-center gap-1">
					{backLink}
					<h1 className="min-w-0 truncate text-base font-semibold">{name}</h1>
					<span className="shrink-0 text-sm text-muted-foreground">
						· {circle.name}
					</span>
				</div>

				<div
					ref={setInsightsElement}
					className="mx-auto max-w-[var(--rsf-post-max-width)]"
				>
					<PersonInsights person={person.data} />
				</div>

				{error && !data ? (
					<div className="space-y-3 py-6 text-center">
						<p className="text-sm text-muted-foreground">
							{t("pages.people.page.error_message")}
						</p>
						<Button variant="outline" size="sm" onClick={() => refetch()}>
							{t("pages.feed.retry")}
						</Button>
					</div>
				) : (
					<VirtualFeed
						items={keeps}
						scrollMargin={feedTop}
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
										{t("pages.people.page.end", { name })}
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
									{t("pages.people.page.empty_title")}
								</h2>
								<p className="text-subtitle">
									{t("pages.people.page.empty_message", { name })}
								</p>
							</div>
						)}
						aria-label={t("pages.people.page.aria_label", { name })}
					/>
				)}
			</div>
		</Layout>
	);
}
