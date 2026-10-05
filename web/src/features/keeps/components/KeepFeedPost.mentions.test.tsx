import "@/i18n/config";
import { renderWithQueryClient } from "@/test-utils";
import { act, fireEvent, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { keepServices } from "../api/services";
import { useFeedKeep } from "../hooks/useKeepFeed";
import type { FeedComment, FeedKeep, KeepCommentRecord } from "../types";
import { KeepFeedPost } from "./KeepFeedPost";

const grandma = { id: 21, display_name: "Grandma Jo" };
const uncle = { id: 22, display_name: "Uncle Bob" };

const makeKeep = (recent_comments: FeedComment[] = []): FeedKeep => ({
	id: "11111111-1111-1111-1111-111111111111",
	circle: { id: 1, name: "Merza Family", slug: "merza-family" },
	created_by: 7,
	created_by_display_name: "Leo",
	title: "Beach day",
	description: "",
	date_of_memory: "2026-07-04T00:00:00Z",
	created_at: "2026-07-05T10:00:00Z",
	media: [],
	reaction_count: 0,
	comment_count: recent_comments.length,
	viewer_reaction: null,
	favorited: false,
	can_delete: false,
	recent_comments,
});

const comment = (overrides: Partial<FeedComment> = {}): FeedComment => ({
	id: 5,
	user: 8,
	user_display_name: "Pat",
	parent: null,
	comment: "So sweet",
	mentions: [],
	can_delete: false,
	created_at: "2026-07-05T11:00:00Z",
	...overrides,
});

const record = (text: string): KeepCommentRecord => ({
	...comment({ id: 99, user: 7, user_display_name: "Leo", comment: text }),
	keep: makeKeep().id,
	updated_at: "2026-07-06T09:00:00Z",
});

function CachedPost({ keepId }: { keepId: string }) {
	const { data } = useFeedKeep(keepId);
	return data ? <KeepFeedPost keep={data} /> : null;
}

async function renderPost(keep: FeedKeep = makeKeep()) {
	vi.spyOn(keepServices, "getFeedKeep").mockResolvedValue(keep);
	renderWithQueryClient(<CachedPost keepId={keep.id} />);
	await screen.findByRole("article");
	return screen.getByRole("textbox", { name: "Add a comment" });
}

const type = (input: HTMLElement, value: string) =>
	fireEvent.change(input, { target: { value } });

const post = () =>
	act(async () =>
		fireEvent.click(screen.getByRole("button", { name: "Post" })),
	);

let getMentionable: ReturnType<typeof vi.fn>;

beforeEach(() => {
	getMentionable = vi
		.spyOn(keepServices, "getMentionableMembers")
		.mockResolvedValue([grandma, uncle]) as unknown as ReturnType<typeof vi.fn>;
});

afterEach(() => {
	vi.restoreAllMocks();
});

describe("@mention autocomplete", () => {
	it("suggests circle members after @ and sends the picked one's id", async () => {
		const addComment = vi
			.spyOn(keepServices, "addComment")
			.mockResolvedValue(record("Look @Grandma Jo hi"));
		const input = await renderPost();

		type(input, "Look @gr");
		const list = await screen.findByRole("list", { name: "People to mention" });
		expect(within(list).getAllByRole("button")).toHaveLength(1);
		expect(getMentionable).toHaveBeenCalledWith(1);

		fireEvent.click(within(list).getByRole("button", { name: "Grandma Jo" }));
		expect(input).toHaveValue("Look @Grandma Jo ");
		expect(
			screen.queryByRole("list", { name: "People to mention" }),
		).toBeNull();

		type(input, "Look @Grandma Jo hi");
		await post();

		expect(addComment).toHaveBeenCalledWith(
			makeKeep().id,
			"Look @Grandma Jo hi",
			undefined,
			[21],
		);
	});

	it("picks with the arrow keys and Enter without posting", async () => {
		const addComment = vi.spyOn(keepServices, "addComment");
		const input = await renderPost();

		type(input, "@");
		await screen.findByRole("list", { name: "People to mention" });
		fireEvent.keyDown(input, { key: "ArrowDown" });
		fireEvent.keyDown(input, { key: "Enter" });

		expect(input).toHaveValue("@Uncle Bob ");
		expect(addComment).not.toHaveBeenCalled();
	});

	it("closes the suggestions on Escape", async () => {
		const input = await renderPost();

		type(input, "@u");
		await screen.findByRole("list", { name: "People to mention" });
		fireEvent.keyDown(input, { key: "Escape" });

		expect(
			screen.queryByRole("list", { name: "People to mention" }),
		).toBeNull();
	});

	it("drops a picked mention whose name was edited out", async () => {
		const addComment = vi
			.spyOn(keepServices, "addComment")
			.mockResolvedValue(record("never mind"));
		const input = await renderPost();

		type(input, "@gr");
		fireEvent.click(await screen.findByRole("button", { name: "Grandma Jo" }));
		type(input, "never mind");
		await post();

		expect(addComment).toHaveBeenCalledWith(
			makeKeep().id,
			"never mind",
			undefined,
			[],
		);
	});

	it("doesn't suggest anyone for an @ inside a word", async () => {
		const input = await renderPost();

		type(input, "mail me@gr");

		expect(
			screen.queryByRole("list", { name: "People to mention" }),
		).toBeNull();
		expect(getMentionable).not.toHaveBeenCalled();
	});
});

describe("mention highlighting", () => {
	it("highlights the members a comment mentions and nothing else", async () => {
		await renderPost(
			makeKeep([
				comment({
					comment: "@Grandma Jo look, @Nobody",
					mentions: [grandma],
				}),
			]),
		);

		const mention = screen.getByText("@Grandma Jo");
		expect(mention).toHaveAttribute("data-mention");
		expect(screen.getByText(/look, @Nobody/)).not.toHaveAttribute(
			"data-mention",
		);
	});

	it("shows comments without mentions as plain text, with their reply button", async () => {
		await renderPost(makeKeep([comment({ mentions: undefined })]));

		expect(screen.getByText("So sweet")).toBeInTheDocument();
		expect(document.querySelector("[data-mention]")).toBeNull();
		expect(screen.getByRole("button", { name: "Reply" })).toBeInTheDocument();
	});
});
