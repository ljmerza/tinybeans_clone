import { EmptyState, Layout } from "@/components";
import { Button } from "@/components/ui/button";
import {
	type Album,
	AlbumFormDialog,
	useAdminCircleIds,
	useAlbums,
} from "@/features/albums";
import { Link, useNavigate } from "@tanstack/react-router";
import { Images, Plus } from "lucide-react";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

function AlbumCard({
	album,
	showCircle,
}: { album: Album; showCircle: boolean }) {
	const { t } = useTranslation();
	return (
		<Link
			to="/albums/$albumId"
			params={{ albumId: album.id }}
			className="group block rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
		>
			<div className="aspect-square overflow-hidden rounded-lg bg-muted">
				{album.cover ? (
					<img
						src={album.cover.url}
						alt=""
						loading="lazy"
						decoding="async"
						className="size-full object-cover transition-transform group-hover:scale-[1.02]"
					/>
				) : (
					<div className="flex size-full items-center justify-center">
						<Images
							className="size-8 text-muted-foreground"
							strokeWidth={1.5}
							aria-hidden="true"
						/>
					</div>
				)}
			</div>
			<p className="mt-1.5 truncate text-sm font-medium">{album.name}</p>
			<p className="truncate text-xs text-muted-foreground">
				{t("pages.albums.post_count", { count: album.post_count })}
				{showCircle ? ` · ${album.circle.name}` : null}
			</p>
		</Link>
	);
}

/**
 * Every album in the viewer's circles as a grid of cover cards, most
 * recently changed first. No page title: the nav already says where you are.
 */
export function AlbumsRouteView() {
	const { t } = useTranslation();
	const navigate = useNavigate();
	const [creating, setCreating] = useState(false);
	const canCreate = useAdminCircleIds().size > 0;
	const {
		data,
		isLoading,
		error,
		refetch,
		fetchNextPage,
		hasNextPage,
		isFetchingNextPage,
	} = useAlbums();

	const albums = useMemo(
		() => data?.pages.flatMap((page) => page.results) ?? [],
		[data],
	);
	// Only worth saying which circle an album is in when there's more than one.
	const showCircle = new Set(albums.map((album) => album.circle.id)).size > 1;

	if (isLoading && !data) {
		return (
			<Layout.Loading
				showHeader={false}
				message={t("pages.albums.loading")}
				spinnerSize="sm"
			/>
		);
	}

	if (error && !data) {
		return (
			<Layout.Error
				title={t("pages.albums.error_title")}
				message={t("pages.albums.error_message")}
				actionLabel={t("pages.feed.retry")}
				onAction={() => refetch()}
			/>
		);
	}

	// Only circle admins create albums.
	const newAlbumButton = canCreate ? (
		<Button className="shrink-0" onClick={() => setCreating(true)}>
			<Plus aria-hidden="true" />
			{t("pages.albums.new_album")}
		</Button>
	) : null;

	return (
		<Layout>
			{/* Layout's <main> already applies container-page padding. */}
			<div className="mx-auto max-w-3xl space-y-4">
				{albums.length === 0 ? (
					<EmptyState
						title={t("pages.albums.empty_title")}
						description={t("pages.albums.empty_message")}
						actions={newAlbumButton}
					/>
				) : (
					<>
						{newAlbumButton && (
							<div className="flex justify-end">{newAlbumButton}</div>
						)}
						<ul
							className="grid grid-cols-2 gap-x-3 gap-y-4 sm:grid-cols-3"
							aria-label={t("pages.albums.aria_label")}
						>
							{albums.map((album) => (
								<li key={album.id}>
									<AlbumCard album={album} showCircle={showCircle} />
								</li>
							))}
						</ul>
						{hasNextPage && (
							<div className="text-center">
								<Button
									variant="outline"
									size="sm"
									disabled={isFetchingNextPage}
									onClick={() => void fetchNextPage({ cancelRefetch: false })}
								>
									{t("pages.albums.show_more")}
								</Button>
							</div>
						)}
					</>
				)}
			</div>
			{creating && (
				<AlbumFormDialog
					open
					onOpenChange={setCreating}
					onSaved={(album) =>
						void navigate({
							to: "/albums/$albumId",
							params: { albumId: album.id },
						})
					}
				/>
			)}
		</Layout>
	);
}
