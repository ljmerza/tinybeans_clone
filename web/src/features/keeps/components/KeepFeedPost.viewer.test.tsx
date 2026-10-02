import "@/i18n/config";
import { renderWithQueryClient } from "@/test-utils";
import { act, fireEvent } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { FeedKeep, FeedMedia } from "../types";
import { KeepFeedPost } from "./KeepFeedPost";

const photo = (id: number, withOriginal = true): FeedMedia => ({
	id,
	media_type: "photo",
	url: `https://cdn.test/gallery/${id}.jpg`,
	...(withOriginal
		? { original_url: `https://cdn.test/original/${id}.jpg` }
		: {}),
	poster_url: null,
	width: 1080,
	height: 1350,
	caption: "",
});

const makeKeep = (media: FeedMedia[]): FeedKeep => ({
	id: "11111111-1111-1111-1111-111111111111",
	circle: { id: 1, name: "Merza Family", slug: "merza-family" },
	created_by: 7,
	created_by_display_name: "Leo",
	title: "Beach day",
	description: "",
	date_of_memory: "2026-07-04T00:00:00Z",
	created_at: "2026-07-05T10:00:00Z",
	media,
	reaction_count: 0,
	comment_count: 0,
	viewer_reaction: null,
	favorited: false,
	can_delete: false,
	recent_comments: [],
});

function tap(element: Element) {
	fireEvent.pointerDown(element, { clientX: 50, clientY: 50 });
	fireEvent.pointerUp(element, { clientX: 50, clientY: 50 });
}

const viewerImage = (src: string) =>
	document.body.querySelector(`.yarl__root img[src="${src}"]`);

beforeEach(() => {
	vi.useFakeTimers();
});

afterEach(() => {
	vi.useRealTimers();
});

describe("KeepFeedPost photo viewer", () => {
	it("opens the full-size photo that was tapped", () => {
		const { container } = renderWithQueryClient(
			<KeepFeedPost keep={makeKeep([photo(1), photo(2)])} />,
		);
		const secondPhoto = container.querySelectorAll(
			".rsf-post__media-slide img",
		)[1];

		tap(secondPhoto);
		// Waits out the double-tap window first.
		expect(document.body.querySelector(".yarl__root")).toBeNull();
		act(() => {
			vi.advanceTimersByTime(350);
		});

		expect(viewerImage("https://cdn.test/original/2.jpg")).not.toBeNull();
	});

	it("leaves a double-tap to like the post", () => {
		const { container } = renderWithQueryClient(
			<KeepFeedPost keep={makeKeep([photo(1)])} />,
		);
		const image = container.querySelector(
			".rsf-post__media-slide img",
		) as Element;

		tap(image);
		act(() => {
			vi.advanceTimersByTime(100);
		});
		tap(image);
		act(() => {
			vi.advanceTimersByTime(400);
		});

		expect(document.body.querySelector(".yarl__root")).toBeNull();
	});

	it("falls back to the feed image for data cached before originals were sent", () => {
		const { container } = renderWithQueryClient(
			<KeepFeedPost keep={makeKeep([photo(3, false)])} />,
		);

		tap(container.querySelector(".rsf-post__media-slide img") as Element);
		act(() => {
			vi.advanceTimersByTime(350);
		});

		expect(viewerImage("https://cdn.test/gallery/3.jpg")).not.toBeNull();
	});
});
