import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { useSwipeNavigation } from "./useSwipeNavigation";

function Harness({
	onSwipeLeft,
	onSwipeRight,
}: {
	onSwipeLeft: () => void;
	onSwipeRight: () => void;
}) {
	const ref = useSwipeNavigation<HTMLDivElement>({ onSwipeLeft, onSwipeRight });
	return (
		<div ref={ref} data-testid="area">
			<p data-testid="text">Caption</p>
			<div className="rsf-post__media-track" data-testid="track">
				<img alt="" />
			</div>
		</div>
	);
}

function touch(
	target: Element,
	type: string,
	x: number,
	y: number,
	time: number,
) {
	const event = new Event(type, { bubbles: true });
	const point = { clientX: x, clientY: y };
	Object.defineProperties(event, {
		touches: { value: type === "touchend" ? [] : [point] },
		changedTouches: { value: [point] },
		timeStamp: { value: time },
	});
	target.dispatchEvent(event);
}

function swipe(
	target: Element,
	fromX: number,
	toX: number,
	{ dy = 0, ms = 200 } = {},
) {
	touch(target, "touchstart", fromX, 300, 1000);
	touch(target, "touchend", toX, 300 + dy, 1000 + ms);
}

// Carousel scroll position: `at` px scrolled of a track `slides` photos wide.
function placeTrack(track: HTMLElement, at: number, slides: number) {
	Object.defineProperties(track, {
		scrollLeft: { value: at, configurable: true },
		clientWidth: { value: 300, configurable: true },
		scrollWidth: { value: 300 * slides, configurable: true },
	});
}

function setup() {
	const onSwipeLeft = vi.fn();
	const onSwipeRight = vi.fn();
	const view = render(
		<Harness onSwipeLeft={onSwipeLeft} onSwipeRight={onSwipeRight} />,
	);
	return {
		onSwipeLeft,
		onSwipeRight,
		text: view.getByTestId("text"),
		track: view.getByTestId("track"),
	};
}

describe("useSwipeNavigation", () => {
	it("reports a left and a right swipe", () => {
		const { onSwipeLeft, onSwipeRight, text } = setup();

		swipe(text, 300, 150);
		expect(onSwipeLeft).toHaveBeenCalledTimes(1);

		swipe(text, 150, 300);
		expect(onSwipeRight).toHaveBeenCalledTimes(1);
	});

	it("ignores short, mostly vertical, and slow swipes", () => {
		const { onSwipeLeft, onSwipeRight, text } = setup();

		swipe(text, 300, 270);
		swipe(text, 300, 150, { dy: 200 });
		swipe(text, 300, 150, { ms: 1500 });

		expect(onSwipeLeft).not.toHaveBeenCalled();
		expect(onSwipeRight).not.toHaveBeenCalled();
	});

	it("lets a photo carousel scroll before it counts as a swipe", () => {
		const { onSwipeLeft, onSwipeRight, track } = setup();

		// Middle photo of three: the carousel takes both directions.
		placeTrack(track, 300, 3);
		swipe(track, 300, 150);
		swipe(track, 150, 300);
		expect(onSwipeLeft).not.toHaveBeenCalled();
		expect(onSwipeRight).not.toHaveBeenCalled();

		// Last photo: swiping on leaves; swiping back stays in the carousel.
		placeTrack(track, 600, 3);
		swipe(track, 300, 150);
		swipe(track, 150, 300);
		expect(onSwipeLeft).toHaveBeenCalledTimes(1);
		expect(onSwipeRight).not.toHaveBeenCalled();

		// First photo: swiping back leaves.
		placeTrack(track, 0, 3);
		swipe(track, 150, 300);
		expect(onSwipeRight).toHaveBeenCalledTimes(1);
	});

	it("treats a single photo as both ends of its carousel", () => {
		const { onSwipeLeft, onSwipeRight, track } = setup();
		placeTrack(track, 0, 1);

		swipe(track, 300, 150);
		swipe(track, 150, 300);

		expect(onSwipeLeft).toHaveBeenCalledTimes(1);
		expect(onSwipeRight).toHaveBeenCalledTimes(1);
	});
});
