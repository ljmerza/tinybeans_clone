import "@/i18n/config";
import { renderWithQueryClient } from "@/test-utils";
import { fireEvent, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Layout pulls in the auth session and router; this suite only cares about the
// feed inside it.
vi.mock("@/components", async (importOriginal) => {
	const actual = await importOriginal<typeof import("@/components")>();
	const Layout = ({ children }: { children?: ReactNode }) => (
		<main>{children}</main>
	);
	Layout.Loading = ({ message }: { message?: string }) => <p>{message}</p>;
	Layout.Error = ({ title }: { title?: string }) => <p>{title}</p>;
	return { ...actual, Layout };
});

import {
	type FeedKeep,
	ON_THIS_DAY_SEED_KEY,
	keepServices,
	localDate,
	onThisDaySlots,
} from "@/features/keeps";
import { HomeFeedView } from "./home-feed";

const keep = (n: number): FeedKeep => ({
	id: `00000000-0000-0000-0000-00000000000${n}`,
	circle: { id: 1, name: "Family", slug: "family" },
	created_by: 1,
	created_by_display_name: "Leo",
	title: `Memory ${n}`,
	description: "",
	date_of_memory: "2026-07-04T00:00:00Z",
	created_at: "2026-07-04T00:00:00Z",
	media: [
		{
			id: n,
			media_type: "photo",
			url: `https://cdn.test/${n}.jpg`,
			poster_url: null,
			width: 800,
			height: 600,
			caption: "",
		},
	],
	reaction_count: 0,
	comment_count: 0,
	viewer_reaction: null,
	favorited: false,
	can_delete: false,
	recent_comments: [],
});

beforeEach(() => {
	// jsdom has no scrolling; the window virtualizer calls this on mount.
	vi.spyOn(window, "scrollTo").mockImplementation(() => {});
	vi.spyOn(keepServices, "getOnThisDay").mockResolvedValue({
		date: "2026-07-04",
		results: [],
	});
});

afterEach(() => {
	window.sessionStorage.clear();
	vi.restoreAllMocks();
});

describe("HomeFeedView", () => {
	it("renders the feed and follows the cursor to the next page", async () => {
		const getFeed = vi
			.spyOn(keepServices, "getFeed")
			.mockImplementation(async (cursor) =>
				cursor
					? { next: null, previous: null, results: [keep(2)] }
					: {
							next: "http://web:8000/api/keeps/feed/?cursor=abc",
							previous: null,
							results: [keep(1)],
						},
			);

		renderWithQueryClient(<HomeFeedView />);

		expect(
			await screen.findByRole("heading", { name: "Memory 1" }),
		).toBeInTheDocument();
		// A one-post page leaves the end of the list in view, so it pages on.
		expect(
			await screen.findByRole("heading", { name: "Memory 2" }),
		).toBeInTheDocument();
		expect(getFeed).toHaveBeenNthCalledWith(1, undefined, {});
		expect(getFeed).toHaveBeenNthCalledWith(2, "abc", {});
		expect(
			await screen.findByText("You're all caught up."),
		).toBeInTheDocument();
		expect(
			screen.getByRole("feed", { name: "Photo feed" }),
		).toBeInTheDocument();
	});

	it("only mounts the posts near the viewport", async () => {
		// jsdom has no layout; give measured rows a real height.
		vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockImplementation(
			function (this: HTMLElement) {
				return this.classList.contains("rsf-virtual-feed__item") ? 500 : 0;
			},
		);
		vi.spyOn(keepServices, "getFeed").mockResolvedValue({
			next: null,
			previous: null,
			results: Array.from({ length: 30 }, (_, i) => keep(i + 1)),
		});

		renderWithQueryClient(<HomeFeedView />);

		expect(
			await screen.findByRole("heading", { name: "Memory 1" }),
		).toBeInTheDocument();
		expect(screen.queryByRole("heading", { name: "Memory 30" })).toBeNull();
		expect(screen.getAllByRole("article").length).toBeLessThan(30);
	});

	it("mixes in this day's memories at the session's seeded slot", async () => {
		window.sessionStorage.setItem(ON_THIS_DAY_SEED_KEY, "1");
		const [slot] = onThisDaySlots(1, 1);
		const memory = {
			...keep(9),
			id: "99999999-0000-0000-0000-000000000000",
			title: "Years back",
		};
		const getOnThisDay = vi
			.spyOn(keepServices, "getOnThisDay")
			.mockResolvedValue({ date: "2026-07-04", results: [memory] });
		vi.spyOn(keepServices, "getFeed").mockResolvedValue({
			next: null,
			previous: null,
			results: Array.from({ length: 12 }, (_, i) => ({
				...keep(i),
				id: `00000000-0000-0000-0000-0000000000${10 + i}`,
				title: `Memory ${i}`,
			})),
		});

		renderWithQueryClient(<HomeFeedView />);

		const card = await screen.findByRole("region", { name: /on this day/i });
		expect(card).toHaveTextContent("Years back");
		expect(getOnThisDay).toHaveBeenCalledWith(localDate(new Date()));
		// Right between the posts either side of its slot.
		const before = screen.getByRole("heading", { name: `Memory ${slot - 1}` });
		const after = screen.getByRole("heading", { name: `Memory ${slot}` });
		expect(
			before.compareDocumentPosition(card) & Node.DOCUMENT_POSITION_FOLLOWING,
		).toBeTruthy();
		expect(
			card.compareDocumentPosition(after) & Node.DOCUMENT_POSITION_FOLLOWING,
		).toBeTruthy();
	});

	it("shows an empty state when there are no photos", async () => {
		vi.spyOn(keepServices, "getFeed").mockResolvedValue({
			next: null,
			previous: null,
			results: [],
		});

		renderWithQueryClient(<HomeFeedView />);

		expect(await screen.findByText("No photos yet")).toBeInTheDocument();
	});

	it("stops paging after a failed page and offers a retry", async () => {
		const getFeed = vi
			.spyOn(keepServices, "getFeed")
			.mockImplementation(async (cursor) => {
				if (cursor) {
					// Fail like a real request would: after a round trip, so the
					// feed renders its in-flight state in between.
					await new Promise((resolve) => setTimeout(resolve, 20));
					throw new Error("boom");
				}
				return {
					next: "http://web:8000/api/keeps/feed/?cursor=abc",
					previous: null,
					results: [keep(1)],
				};
			});

		renderWithQueryClient(<HomeFeedView />);

		const retry = await screen.findByRole("button", { name: "Try again" });
		expect(screen.getByText("Couldn't load more photos.")).toBeInTheDocument();
		// A failed page must not immediately re-trigger another request.
		await new Promise((resolve) => setTimeout(resolve, 200));
		expect(getFeed).toHaveBeenCalledTimes(2);

		getFeed.mockImplementation(async () => ({
			next: null,
			previous: null,
			results: [keep(2)],
		}));
		fireEvent.click(retry);

		expect(
			await screen.findByRole("heading", { name: "Memory 2" }),
		).toBeInTheDocument();
		expect(getFeed).toHaveBeenCalledTimes(3);
	});

	it("shows text posts without media", async () => {
		vi.spyOn(keepServices, "getFeed").mockResolvedValue({
			next: null,
			previous: null,
			results: [{ ...keep(1), description: "First steps today!", media: [] }],
		});

		renderWithQueryClient(<HomeFeedView />);

		expect(await screen.findByText("First steps today!")).toBeInTheDocument();
		expect(screen.queryByRole("img")).toBeNull();
	});

	it("opens the composer from the New post button", async () => {
		vi.spyOn(keepServices, "getFeed").mockResolvedValue({
			next: null,
			previous: null,
			results: [],
		});
		// Loaded here: a static import ahead of the view loads the real Layout.
		const { circleServices } = await import("@/features/circles");
		const listMemberships = vi
			.spyOn(circleServices, "listMemberships")
			.mockResolvedValue({ data: { circles: [] } });

		renderWithQueryClient(<HomeFeedView />);
		await screen.findByText("No photos yet");
		// The composer (and its circle lookup) only loads once opened.
		expect(listMemberships).not.toHaveBeenCalled();

		fireEvent.click(screen.getByRole("button", { name: "New post" }));

		expect(
			await screen.findByRole("dialog", { name: "New post" }),
		).toBeInTheDocument();
		expect(listMemberships).toHaveBeenCalled();
	});

	it("shows an error state when the first page fails", async () => {
		vi.spyOn(keepServices, "getFeed").mockRejectedValue(new Error("boom"));

		renderWithQueryClient(<HomeFeedView />);

		expect(
			await screen.findByText("Couldn't load your feed"),
		).toBeInTheDocument();
	});
});
