import { useEffect, useRef } from "react";

// A swipe must travel this far sideways...
const MIN_DISTANCE_PX = 60;
// ...mostly sideways...
const HORIZONTAL_RATIO = 1.5;
// ...and quickly, so a slow drag or a scroll isn't read as one.
const MAX_DURATION_MS = 800;

export interface SwipeNavigationHandlers {
	/** Finger moved right to left. */
	onSwipeLeft?: () => void;
	/** Finger moved left to right. */
	onSwipeRight?: () => void;
}

/**
 * Sideways swipes anywhere inside the returned ref's element. A swipe that
 * starts on a photo carousel scrolls the carousel first: it only counts once
 * the carousel is already at its last (or first) photo.
 *
 * Native listeners, not React's: React bubbles events out of portals, so a
 * swipe inside a dialog or photo viewer would otherwise count too.
 */
export function useSwipeNavigation<T extends HTMLElement>(
	handlers: SwipeNavigationHandlers,
) {
	const ref = useRef<T | null>(null);
	const handlersRef = useRef(handlers);
	handlersRef.current = handlers;

	useEffect(() => {
		const element = ref.current;
		if (!element) return;

		let start: {
			x: number;
			y: number;
			time: number;
			atFirst: boolean;
			atLast: boolean;
		} | null = null;

		const onTouchStart = (event: TouchEvent) => {
			const target = event.target as Element;
			if (
				event.touches.length !== 1 ||
				target.closest('input, textarea, select, [contenteditable="true"]')
			) {
				start = null;
				return;
			}
			const track = target.closest(".rsf-post__media-track");
			const touch = event.touches[0];
			start = {
				x: touch.clientX,
				y: touch.clientY,
				time: event.timeStamp,
				atFirst: !track || track.scrollLeft <= 1,
				atLast:
					!track ||
					track.scrollLeft + track.clientWidth >= track.scrollWidth - 1,
			};
		};

		const onTouchEnd = (event: TouchEvent) => {
			const swipe = start;
			start = null;
			const touch = event.changedTouches[0];
			if (!swipe || !touch) return;
			const dx = touch.clientX - swipe.x;
			const dy = touch.clientY - swipe.y;
			if (
				event.timeStamp - swipe.time > MAX_DURATION_MS ||
				Math.abs(dx) < MIN_DISTANCE_PX ||
				Math.abs(dx) < HORIZONTAL_RATIO * Math.abs(dy)
			) {
				return;
			}
			if (dx < 0 && swipe.atLast) handlersRef.current.onSwipeLeft?.();
			else if (dx > 0 && swipe.atFirst) handlersRef.current.onSwipeRight?.();
		};

		const onTouchCancel = () => {
			start = null;
		};

		element.addEventListener("touchstart", onTouchStart, { passive: true });
		element.addEventListener("touchend", onTouchEnd, { passive: true });
		element.addEventListener("touchcancel", onTouchCancel, { passive: true });
		return () => {
			element.removeEventListener("touchstart", onTouchStart);
			element.removeEventListener("touchend", onTouchEnd);
			element.removeEventListener("touchcancel", onTouchCancel);
		};
	}, []);

	return ref;
}
