import { ConfirmDialog, Layout, LoadingState } from "@/components";
import { Button } from "@/components/ui/button";
import {
	AlbumCoverAction,
	AlbumFormDialog,
	useAlbum,
	useAlbumKeeps,
	useDeleteAlbum,
} from "@/features/albums";
import { KeepFeedPost } from "@/features/keeps";
import { Link, getRouteApi, useNavigate } from "@tanstack/react-router";
import { ArrowLeft, Pencil, Trash2 } from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import "react-social-feed/styles.css";
import { VirtualFeed } from "react-social-feed/virtual";

const route = getRouteApi("/albums/$albumId");

/**
 * One album's posts, oldest memory first. Just a compact line with the
 * album's name and count above the posts; circle admins also get edit and
 * delete buttons there, and can pick any post with a photo as the cover.
 */
export function AlbumRouteView() {
	const { t } = useTranslation();
	const { albumId } = route.useParams();
	const navigate = useNavigate();
	const album = useAlbum(albumId);
	const {
		data,
		error,
		refetch,
		fetchNextPage,
		hasNextPage,
		isFetchingNextPage,
		isFetchNextPageError,
	} = useAlbumKeeps(albumId);
	const deleteAlbum = useDeleteAlbum();
	const [editing, setEditing] = useState(false);
	const [confirmingDelete, setConfirmingDelete] = useState(false);

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

	const confirmDelete = async () => {
		try {
			await deleteAlbum.mutateAsync(albumId);
			setConfirmingDelete(false);
			void navigate({ to: "/albums" });
		} catch {
			// The mutation's error toast explains it; leave the dialog open to retry.
		}
	};

	if (album.isLoading || (!data && !error)) {
		return (
			<Layout.Loading
				showHeader={false}
				message={t("pages.albums.album_loading")}
				spinnerSize="sm"
			/>
		);
	}

	const backLink = (
		<Link
			to="/albums"
			aria-label={t("pages.albums.back")}
			title={t("pages.albums.back")}
			className="-ml-2 inline-flex size-9 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
		>
			<ArrowLeft className="size-5" aria-hidden="true" />
		</Link>
	);

	if (!album.data) {
		return (
			<Layout>
				<div className="mx-auto max-w-[var(--rsf-post-max-width)] py-16 text-center">
					<h1 className="heading-3 mb-2">
						{t("pages.albums.not_found_title")}
					</h1>
					<p className="text-subtitle mb-6">
						{t("pages.albums.not_found_message")}
					</p>
					<Link to="/albums" className="text-sm underline underline-offset-4">
						{t("pages.albums.back")}
					</Link>
				</div>
			</Layout>
		);
	}

	const current = album.data;
	const { name, description, post_count: postCount, can_edit } = current;

	return (
		<Layout>
			{/* Layout's <main> already applies container-page padding. */}
			<div className="space-y-4">
				<div className="mx-auto max-w-[var(--rsf-post-max-width)]">
					<div className="flex items-center gap-1">
						{backLink}
						<h1 className="min-w-0 truncate text-base font-semibold">{name}</h1>
						<span className="shrink-0 text-sm text-muted-foreground">
							· {t("pages.albums.post_count", { count: postCount })}
						</span>
						{can_edit && (
							<span className="ml-auto flex shrink-0">
								<Button
									variant="ghost"
									size="icon"
									className="size-9 text-muted-foreground"
									aria-label={t("pages.albums.rename")}
									onClick={() => setEditing(true)}
								>
									<Pencil aria-hidden="true" />
								</Button>
								<Button
									variant="ghost"
									size="icon"
									className="size-9 text-muted-foreground hover:text-destructive"
									aria-label={t("pages.albums.delete")}
									onClick={() => setConfirmingDelete(true)}
								>
									<Trash2 aria-hidden="true" />
								</Button>
							</span>
						)}
					</div>
					{description && (
						<p className="whitespace-pre-line text-sm text-muted-foreground">
							{description}
						</p>
					)}
				</div>

				{error && !data ? (
					<div className="space-y-3 py-6 text-center">
						<p className="text-sm text-muted-foreground">
							{t("pages.albums.error_message")}
						</p>
						<Button variant="outline" size="sm" onClick={() => refetch()}>
							{t("pages.feed.retry")}
						</Button>
					</div>
				) : (
					<VirtualFeed
						items={keeps}
						getItemKey={(keep) => keep.id}
						renderItem={(keep) => (
							<KeepFeedPost
								keep={keep}
								extraActions={
									can_edit && <AlbumCoverAction album={current} keep={keep} />
								}
							/>
						)}
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
										{t("pages.albums.album_end")}
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
									{t("pages.albums.album_empty_title")}
								</h2>
								<p className="text-subtitle">
									{t("pages.albums.album_empty_message")}
								</p>
							</div>
						)}
						aria-label={t("pages.albums.album_aria_label", { name })}
					/>
				)}
			</div>
			{editing && (
				<AlbumFormDialog open onOpenChange={setEditing} album={album.data} />
			)}
			<ConfirmDialog
				open={confirmingDelete}
				onOpenChange={setConfirmingDelete}
				title={t("pages.albums.delete_title")}
				description={t("pages.albums.delete_description")}
				confirmLabel={t("pages.albums.delete_confirm")}
				cancelLabel={t("common.cancel")}
				variant="destructive"
				isLoading={deleteAlbum.isPending}
				onConfirm={confirmDelete}
			/>
		</Layout>
	);
}
