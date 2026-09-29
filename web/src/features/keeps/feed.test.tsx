import "@/i18n/config";
import { renderWithQueryClient } from "@/test-utils";
import {
	act,
	fireEvent,
	screen,
	waitFor,
	within,
} from "@testing-library/react";
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
	favorited: false,
	recent_comments: [
		{
			id: 5,
			user: 8,
			user_display_name: "Grandma",
			parent: null,
			comment: "So sweet",
			can_delete: false,
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
	can_delete: true,
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

	it("passes the viewer's favorite through", () => {
		expect(keepToSocialPost(makeKeep(), options).favorited).toBe(false);
		expect(
			keepToSocialPost(makeKeep({ favorited: true }), options).favorited,
		).toBe(true);
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

	it("shows the title above the photo", async () => {
		await renderCachedPost(makeKeep());

		const title = screen.getByRole("heading", { name: "Beach day" });
		const photo = screen.getByRole("img", { name: "Beach day" });
		expect(
			title.compareDocumentPosition(photo) & Node.DOCUMENT_POSITION_FOLLOWING,
		).toBeTruthy();
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

	it("favorites and unfavorites through the favorites API", async () => {
		const favoriteKeep = vi
			.spyOn(keepServices, "favoriteKeep")
			.mockResolvedValue({ favorited: true });
		const unfavoriteKeep = vi
			.spyOn(keepServices, "unfavoriteKeep")
			.mockResolvedValue(undefined);
		await renderCachedPost(makeKeep());

		const button = screen.getByRole("button", { name: "Add to favorites" });
		expect(button).toHaveAttribute("aria-pressed", "false");
		await act(async () => fireEvent.click(button));
		expect(favoriteKeep).toHaveBeenCalledWith(makeKeep().id);
		const saved = await screen.findByRole("button", {
			name: "Remove from favorites",
		});
		expect(saved).toHaveAttribute("aria-pressed", "true");

		await act(async () => fireEvent.click(saved));
		expect(unfavoriteKeep).toHaveBeenCalledWith(makeKeep().id);
		expect(
			await screen.findByRole("button", { name: "Add to favorites" }),
		).toHaveAttribute("aria-pressed", "false");
	});

	it("rolls the favorite back when the request fails", async () => {
		vi.spyOn(keepServices, "favoriteKeep").mockRejectedValue(
			new Error("offline"),
		);
		await renderCachedPost(makeKeep());

		await act(async () =>
			fireEvent.click(screen.getByRole("button", { name: "Add to favorites" })),
		);

		await waitFor(() =>
			expect(
				screen.getByRole("button", { name: "Add to favorites" }),
			).toHaveAttribute("aria-pressed", "false"),
		);
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

		expect(addComment).toHaveBeenCalledWith(
			makeKeep().id,
			"Love it",
			undefined,
		);
		expect(await screen.findByText("Love it")).toBeInTheDocument();
	});

	it("replies to a comment by tagging its author and nests the reply", async () => {
		const addComment = vi
			.spyOn(keepServices, "addComment")
			.mockResolvedValue(
				commentRecord({ id: 100, parent: 5, comment: "@Grandma thank you" }),
			);
		await renderCachedPost(makeKeep());

		fireEvent.click(screen.getByRole("button", { name: "Reply" }));
		const input = screen.getByRole("textbox", { name: "Add a comment" });
		expect(input).toHaveValue("@Grandma ");
		expect(screen.getByText("Replying to Grandma")).toBeInTheDocument();

		fireEvent.change(input, { target: { value: "@Grandma thank you" } });
		await act(async () =>
			fireEvent.click(screen.getByRole("button", { name: "Post" })),
		);

		expect(addComment).toHaveBeenCalledWith(
			makeKeep().id,
			"@Grandma thank you",
			5,
		);
		const reply = await screen.findByText("@Grandma thank you");
		expect(
			screen.getByText("So sweet").closest("li")?.querySelector("ul"),
		).toContainElement(reply);
	});

	it("deletes a comment only after confirming", async () => {
		const deleteComment = vi
			.spyOn(keepServices, "deleteComment")
			.mockResolvedValue(undefined);
		const mine = commentRecord({ id: 6, comment: "Oops" });
		const keep = makeKeep({
			comment_count: 2,
			recent_comments: [...makeKeep().recent_comments, mine],
		});
		await renderCachedPost(keep);
		// The refetch after deleting.
		vi.spyOn(keepServices, "getFeedKeep").mockResolvedValue(makeKeep());

		// Only the viewer's own comment is deletable here.
		const deleteButtons = screen.getAllByRole("button", {
			name: "Delete comment",
		});
		expect(deleteButtons).toHaveLength(1);

		fireEvent.click(deleteButtons[0]);
		expect(
			await screen.findByText(
				"This can't be undone. Any replies to it will be deleted too.",
			),
		).toBeInTheDocument();
		fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
		expect(deleteComment).not.toHaveBeenCalled();

		fireEvent.click(screen.getByRole("button", { name: "Delete comment" }));
		await act(async () =>
			fireEvent.click(await screen.findByRole("button", { name: "Delete" })),
		);

		expect(deleteComment).toHaveBeenCalledWith(6);
		await waitFor(() => expect(screen.queryByText("Oops")).toBeNull());
		expect(screen.getByText("So sweet")).toBeInTheDocument();
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
			screen.getByRole("button", { name: "View more comments (2)" }),
		);

		expect(await screen.findByText("First!")).toBeInTheDocument();
		expect(getKeepComments).toHaveBeenCalledWith(makeKeep().id);
	});

	it("shows every comment when opened expanded, as on a keep's own page", async () => {
		const thread = Array.from({ length: 12 }, (_, n) =>
			commentRecord({ id: n + 1, comment: `comment ${n + 1}` }),
		);
		vi.spyOn(keepServices, "getKeepComments").mockResolvedValue({
			count: 12,
			next: null,
			previous: null,
			results: thread,
		});
		renderWithQueryClient(
			<KeepFeedPost
				keep={makeKeep({ comment_count: 12 })}
				defaultCommentsExpanded
			/>,
		);

		await waitFor(() =>
			expect(screen.queryAllByText(/^comment \d+$/)).toHaveLength(12),
		);
		expect(
			screen.queryByRole("button", { name: /^View more/ }),
		).not.toBeInTheDocument();
	});

	it("shows three comments, then five more per click", async () => {
		const thread = Array.from({ length: 12 }, (_, n) =>
			commentRecord({ id: n + 1, comment: `comment ${n + 1}` }),
		);
		let resolveThread: (value: {
			count: number;
			next: null;
			previous: null;
			results: KeepCommentRecord[];
		}) => void = () => {};
		const getKeepComments = vi
			.spyOn(keepServices, "getKeepComments")
			.mockReturnValue(
				new Promise((resolve) => {
					resolveThread = resolve;
				}),
			);
		await renderCachedPost(
			makeKeep({
				comment_count: 12,
				recent_comments: thread.slice(-3).map((record) => ({
					id: record.id,
					user: record.user,
					user_display_name: record.user_display_name,
					parent: record.parent,
					comment: record.comment,
					can_delete: record.can_delete,
					created_at: record.created_at,
				})),
			}),
		);
		const shown = () => screen.queryAllByText(/^comment \d+$/);

		expect(shown()).toHaveLength(3);
		fireEvent.click(
			screen.getByRole("button", { name: "View more comments (9)" }),
		);
		expect(getKeepComments).toHaveBeenCalledOnce();
		expect(screen.getByRole("status")).toHaveTextContent("Loading comments…");

		resolveThread({ count: 12, next: null, previous: null, results: thread });
		await waitFor(() => expect(shown()).toHaveLength(8));
		expect(screen.queryByText("comment 4")).toBeNull();

		fireEvent.click(
			screen.getByRole("button", { name: "View more comments (4)" }),
		);
		expect(shown()).toHaveLength(12);
		expect(
			screen.queryByRole("button", { name: /^View / }),
		).not.toBeInTheDocument();

		fireEvent.click(screen.getByRole("button", { name: "Hide comments" }));
		expect(shown()).toHaveLength(3);
		expect(getKeepComments).toHaveBeenCalledOnce();
	});

	it("long-pressing like opens who liked it without toggling the like", async () => {
		const addReaction = vi.spyOn(keepServices, "addReaction");
		const getKeepLikers = vi
			.spyOn(keepServices, "getKeepLikers")
			.mockResolvedValue({
				count: 3,
				next: "http://web:8000/api/keeps/feed/x/likers/?limit=2&offset=2",
				previous: null,
				results: [
					{
						id: 11,
						user: 8,
						user_display_name: "Grandma",
						reaction_type: "love",
						created_at: "2026-07-06T09:00:00Z",
					},
					{
						id: 10,
						user: 9,
						user_display_name: "Uncle Sam",
						reaction_type: "like",
						created_at: "2026-07-05T09:00:00Z",
					},
				],
			});
		await renderCachedPost(makeKeep());
		expect(getKeepLikers).not.toHaveBeenCalled();

		const button = likeButton();
		fireEvent.pointerDown(button, { clientX: 5, clientY: 5, button: 0 });
		await act(() => new Promise((resolve) => setTimeout(resolve, 550)));
		fireEvent.pointerUp(button, { clientX: 5, clientY: 5 });
		fireEvent.click(button);

		const dialog = await screen.findByRole("dialog", { name: "Liked by" });
		expect(await within(dialog).findByText("Grandma")).toBeInTheDocument();
		expect(within(dialog).getByText("Uncle Sam")).toBeInTheDocument();
		expect(within(dialog).getByText("And 1 more")).toBeInTheDocument();
		expect(getKeepLikers).toHaveBeenCalledWith(makeKeep().id);
		expect(addReaction).not.toHaveBeenCalled();
		// The open dialog hides the post from queries by role.
		expect(button).toHaveAttribute("aria-pressed", "false");
	});

	it("opens who liked it from the keyboard too", async () => {
		vi.spyOn(keepServices, "getKeepLikers").mockResolvedValue({
			count: 0,
			next: null,
			previous: null,
			results: [],
		});
		await renderCachedPost(makeKeep());

		expect(likeButton()).toHaveAttribute("aria-keyshortcuts", "Shift+Enter");
		fireEvent.keyDown(likeButton(), { key: "Enter", shiftKey: true });

		const dialog = await screen.findByRole("dialog", { name: "Liked by" });
		expect(await within(dialog).findByText("No likes yet")).toBeInTheDocument();
	});
});
