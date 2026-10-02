import { type PointerEvent, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import Lightbox from "yet-another-react-lightbox";
import Zoom from "yet-another-react-lightbox/plugins/zoom";
import "yet-another-react-lightbox/styles.css";

import type { FeedKeep } from "../types";

// A second tap this soon is a double-tap, which likes the post instead.
const DOUBLE_TAP_MS = 300;
// Further than this between press and release is a drag, not a tap.
const TAP_SLOP_PX = 10;

/**
 * Tap a photo in a keep's media to see the full-size original on its own,
 * with pinch/zoom. Spread `mediaProps` onto `<PostMedia>` and render `viewer`.
 * A tap waits out the double-tap window so double-tap still likes the post.
 */
export function useKeepPhotoViewer(keep: FeedKeep) {
	const { t } = useTranslation();
	// Videos already play in place, so only photos open the viewer.
	const photos = useMemo(
		() =>
			keep.media
				.map((media, mediaIndex) => ({ media, mediaIndex }))
				.filter(({ media }) => media.media_type === "photo"),
		[keep.media],
	);
	const [openAt, setOpenAt] = useState<number | null>(null);
	const pressRef = useRef<{ x: number; y: number } | null>(null);
	const tapTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

	useEffect(
		() => () => {
			if (tapTimerRef.current) clearTimeout(tapTimerRef.current);
		},
		[],
	);

	const onPointerDown = (event: PointerEvent<HTMLDivElement>) => {
		pressRef.current = { x: event.clientX, y: event.clientY };
	};

	const onPointerUp = (event: PointerEvent<HTMLDivElement>) => {
		const press = pressRef.current;
		pressRef.current = null;
		const target = event.target as Element;
		if (target.closest("button, a, video")) return;
		if (
			!press ||
			Math.hypot(event.clientX - press.x, event.clientY - press.y) > TAP_SLOP_PX
		) {
			return;
		}
		if (tapTimerRef.current) {
			// Second tap of a double-tap: the post handles it as a like.
			clearTimeout(tapTimerRef.current);
			tapTimerRef.current = null;
			return;
		}
		const slide = target.closest(".rsf-post__media-slide");
		const mediaIndex = slide?.parentElement
			? Array.prototype.indexOf.call(slide.parentElement.children, slide)
			: -1;
		const photoIndex = photos.findIndex(
			(photo) => photo.mediaIndex === mediaIndex,
		);
		if (photoIndex < 0) return;
		tapTimerRef.current = setTimeout(() => {
			tapTimerRef.current = null;
			setOpenAt(photoIndex);
		}, DOUBLE_TAP_MS);
	};

	const viewer =
		openAt === null ? null : (
			<Lightbox
				open
				index={openAt}
				close={() => setOpenAt(null)}
				slides={photos.map(({ media }) => ({
					// Data cached before original_url existed falls back to the feed size.
					src: media.original_url ?? media.url,
					width: media.width ?? undefined,
					height: media.height ?? undefined,
					alt: media.caption || keep.title || undefined,
				}))}
				plugins={[Zoom]}
				carousel={{ finite: true }}
				controller={{ closeOnPullDown: true, closeOnBackdropClick: true }}
				render={
					photos.length > 1
						? undefined
						: { buttonPrev: () => null, buttonNext: () => null }
				}
				labels={{
					Close: t("common.close"),
					Previous: t("pages.feed.previous_photo"),
					Next: t("pages.feed.next_photo"),
					"Zoom in": t("pages.feed.zoom_in"),
					"Zoom out": t("pages.feed.zoom_out"),
				}}
			/>
		);

	return { mediaProps: { onPointerDown, onPointerUp }, viewer };
}
