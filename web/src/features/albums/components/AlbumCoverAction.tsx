import type { FeedKeep } from "@/features/keeps/types";
import { cn } from "@/lib/utils";
import { useIsMutating } from "@tanstack/react-query";
import { BookImage } from "lucide-react";
import { useTranslation } from "react-i18next";
import { PostAction } from "react-social-feed";

import { albumKeys } from "../api/queryKeys";
import { useSetAlbumCover } from "../hooks/useAlbums";
import type { Album } from "../types";

export interface AlbumCoverActionProps {
	album: Album;
	keep: FeedKeep;
}

/**
 * A post action on an album's page for whoever may edit the album: makes the
 * post the album's cover, or, on the chosen cover, goes back to the default
 * (the album's first post). The current cover, chosen or default, is
 * highlighted, with a "Cover" label where there is room. Posts without a
 * photo or video can't be covers.
 */
export function AlbumCoverAction({ album, keep }: AlbumCoverActionProps) {
	const { t } = useTranslation();
	const setCover = useSetAlbumCover(album.id);
	// One change at a time, so answers can't land out of order.
	const busy = useIsMutating({ mutationKey: albumKeys.setCover(album.id) }) > 0;

	if (keep.media.length === 0) return null;

	const isCover = album.cover?.keep_id === keep.id;
	const isChosen = album.cover_keep === keep.id;
	// The default cover is already what a reset would give.
	const isDefaultCover = isCover && !isChosen;

	const label = isChosen
		? t("pages.albums.cover.reset")
		: isDefaultCover
			? t("pages.albums.cover.default")
			: t("pages.albums.cover.set");

	return (
		<PostAction
			active={isCover}
			aria-label={label}
			title={label}
			aria-disabled={isDefaultCover || undefined}
			disabled={busy}
			className={cn(isDefaultCover && "cursor-default!")}
			icon={<BookImage strokeWidth={1.8} />}
			onClick={() => {
				if (isDefaultCover) return;
				setCover.mutate(isChosen ? null : keep.id);
			}}
		>
			{isCover && (
				// Phones show just the highlighted icon; the action row is full there.
				<span aria-hidden="true" className="max-sm:hidden">
					{t("pages.albums.cover.badge")}
				</span>
			)}
		</PostAction>
	);
}
