import "@/i18n/config";
import { renderWithQueryClient } from "@/test-utils";
import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { keepServices } from "./api/services";
import { KeepFeedPost } from "./components/KeepFeedPost";
import { cursorFromNextUrl, useFeedKeep } from "./hooks/useKeepFeed";
import type { FeedKeep, KeepCommentRecord } from "./types";
import { keepToSocialPost } from "./utils/keepToSocialPost";

const makeKeep = (overrides: Partial<FeedKeep> = {}): FeedKeep => ({
	id: "11111111-1111-1111-1111-111111111111",
	circle: { id: 1, name: "Merza Family", slug: "merza-family" },
	created_by: 7,
	created_by_display_name: "Leo",
	title: "Beach day",
	description: "First time in the ocean",
	date_of_memory: "2026-07-04T00:00:00Z",
	created_at: "2026-07-05T10:00:00Z",
	media: [
		{
			id: 1,
			media_type: "photo",
			url: "https://cdn.test/gallery/1.jpg",
			poster_url: null,
			width: 1080,
			height: 1350,
			caption: "",
		},
	],
	reaction_count: 3,
	comment_count: 1,
	viewer_reaction: null,
	recent_comments: [
		{
			id: 5,
			user: 8,
			user_display_name: "Grandma",
			parent: null,
			comment: "So sweet",
			created_at: "2026-07-05T11:00:00Z",
		},
	],
	...overrides,
});

const commentRecord = (
	overrides: Partial<KeepCommentRecord> = {},
): KeepCommentRecord => ({
	id: 99,
	keep: makeKeep().id,
	user: 7,
	user_display_name: "Leo",
	parent: null,
	comment: "Love it",
	created_at: "2026-07-06T09:00:00Z",
	updated_at: "2026-07-06T09:00:00Z",
	...overrides,
});

/** Renders the post from the query cache so mutations' cache writes show up. */
function CachedPost({ keepId }: { keepId: string }) {
	const { data } = useFeedKeep(keepId);
	return data ? <KeepFeedPost keep={data} /> : null;
}

async function renderCachedPost(keep: FeedKeep) {
	vi.spyOn(keepServices, "getFeedKeep").mockResolvedValue(keep);
	renderWithQueryClient(<CachedPost keepId={keep.id} />);
	await screen.findByRole("article");
}

const likeButton = () =>
	screen.getByRole("button", { name: /^(like|unlike)$/i });

afterEach(() => {
	vi.restoreAllMocks();
});

describe("cursorFromNextUrl", () => {
	it("extracts the cursor from DRF's absolute next URL", () => {
		expect(
			cursorFromNextUrl(
				"http://web:8000/api/keeps/feed/?cursor=cD0yMDI2&page_size=10",
			),
		).toBe("cD0yMDI2");
		expect(cursorFromNextUrl(null)).toBeUndefined();
	});
});

describe("keepToSocialPost", () => {
	const options = {
		fallbackAlt: "Photo shared by Leo",
		origin: "https://app.test",
	};

	it("maps a feed keep onto the post shape", () => {
		const post = keepToSocialPost(
			makeKeep({
				viewer_reaction: { id: 4, reaction_type: "love" },
				media: [
					{
						id: 2,
						media_type: "video",
						url: "https://cdn.test/v.mp4",
						poster_url: "https://cdn.test/v.jpg",
						width: null,
						height: null,
						caption: "Splash",
					},
				],
			}),
			options,
		);

		expect(post).toMatchObject({
			title: "Beach day",
			caption: "First time in the ocean",
			author: { name: "Leo" },
			likeCount: 3,
			// Any reaction type counts as liked.
			liked: true,
			commentCount: 1,
			shareUrl: "https://app.test/keeps/11111111-1111-1111-1111-111111111111",
			media: [
				{
					type: "video",
					src: "https://cdn.test/v.mp4",
					poster: "https://cdn.test/v.jpg",
					alt: "Splash",
					width: undefined,
				},
			],
			comments: [{ id: "5", author: { name: "Grandma" }, text: "So sweet" }],
		});
	});

	it("falls back to the title, then a generic alt, and prefers a loaded thread", () => {
		const titled = keepToSocialPost(makeKeep(), options);
		expect(titled.media[0]?.alt).toBe("Beach day");

		const untitled = keepToSocialPost(
			makeKeep({ title: "", description: "" }),
			{
				...options,
				comments: [],
			},
		);
		expect(untitled.media[0]?.alt).toBe("Photo shared by Leo");
		expect(untitled.title).toBeUndefined();
		expect(untitled.caption).toBeUndefined();
		expect(untitled.comments).toEqual([]);
	});
});

describe("KeepFeedPost", () => {
	it("renders the keep with its circle and a UTC memory date", async () => {
		await renderCachedPost(makeKeep());

		expect(
			screen.getByRole("heading", { name: "Beach day" }),
		).toBeInTheDocument();
		expect(screen.getByText(/Merza Family/)).toBeInTheDocument();
		// Midnight UTC must not slip to the previous day in western time zones.
		expect(screen.getByText("Jul 4, 2026")).toBeInTheDocument();
		expect(likeButton()).toHaveTextContent("3");
		expect(screen.getByText("So sweet")).toBeInTheDocument();
	});

	it("likes through the reactions API and keeps the server's reaction id", async () => {
		const addReaction = vi
			.spyOn(keepServices, "addReaction")
			.mockResolvedValue({
				id: 42,
				keep: makeKeep().id,
				user: 7,
				user_display_name: "Leo",
				reaction_type: "like",
				created_at: "2026-07-06T09:00:00Z",
			});
		const removeReaction = vi
			.spyOn(keepServices, "removeReaction")
			.mockResolvedValue(undefined);
		await renderCachedPost(makeKeep());

		await act(async () => fireEvent.click(likeButton()));
		expect(addReaction).toHaveBeenCalledWith(makeKeep().id);
		await waitFor(() => expect(likeButton()).toHaveTextContent("4"));
		expect(likeButton()).toHaveAttribute("aria-pressed", "true");

		await act(async () => fireEvent.click(likeButton()));
		expect(removeReaction).toHaveBeenCalledWith(42);
		await waitFor(() => expect(likeButton()).toHaveTextContent("3"));
	});

	it("rolls the like back when the request fails", async () => {
		vi.spyOn(keepServices, "addReaction").mockRejectedValue(
			new Error("offline"),
		);
		await renderCachedPost(makeKeep());

		await act(async () => fireEvent.click(likeButton()));

		await waitFor(() =>
			expect(likeButton()).toHaveAttribute("aria-pressed", "false"),
		);
		expect(likeButton()).toHaveTextContent("3");
	});

	it("posts a comment and shows it without a refetch", async () => {
		const addComment = vi
			.spyOn(keepServices, "addComment")
			.mockResolvedValue(commentRecord());
		await renderCachedPost(makeKeep());

		fireEvent.change(screen.getByRole("textbox", { name: "Add a comment" }), {
			target: { value: "Love it" },
		});
		await act(async () =>
			fireEvent.click(screen.getByRole("button", { name: "Post" })),
		);

		expect(addComment).toHaveBeenCalledWith(makeKeep().id, "Love it");
		expect(await screen.findByText("Love it")).toBeInTheDocument();
	});

	it("loads the full thread when comments are expanded", async () => {
		const getKeepComments = vi
			.spyOn(keepServices, "getKeepComments")
			.mockResolvedValue({
				count: 3,
				next: null,
				previous: null,
				results: [
					commentRecord({ id: 1, comment: "First!" }),
					commentRecord({ id: 2, comment: "Second" }),
					commentRecord({
						id: 5,
						comment: "So sweet",
						user_display_name: "Grandma",
					}),
				],
			});
		await renderCachedPost(makeKeep({ comment_count: 3 }));

		expect(getKeepComments).not.toHaveBeenCalled();
		fireEvent.click(
			screen.getByRole("button", { name: "View all 3 comments" }),
		);

		expect(await screen.findByText("First!")).toBeInTheDocument();
		expect(getKeepComments).toHaveBeenCalledWith(makeKeep().id);
	});
});
