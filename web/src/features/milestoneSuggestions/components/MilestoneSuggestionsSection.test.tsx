import "@/i18n/config";
import { circleServices } from "@/features/circles";
import type { FeedKeep } from "@/features/keeps/types";
import { renderWithQueryClient } from "@/test-utils";
import {
	act,
	fireEvent,
	screen,
	waitFor,
	within,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { milestoneSuggestionServices } from "../api/services";
import type {
	ListedSuggestionStatus,
	MilestoneSuggestion,
	MilestoneSuggestionPage,
} from "../types";
import { MilestoneSuggestionsSection } from "./MilestoneSuggestionsSection";

const ALBUM_ID = "aaaaaaaa-0000-0000-0000-000000000009";

const keep = (n: number, title: string): FeedKeep => ({
	id: `00000000-0000-0000-0000-00000000000${n}`,
	circle: { id: 7, name: "Family", slug: "family" },
	created_by: 1,
	created_by_display_name: "Leo",
	title,
	description: "",
	date_of_memory: `2026-07-0${n}T00:00:00Z`,
	created_at: `2026-07-0${n}T00:00:00Z`,
	media: [],
	reaction_count: 0,
	comment_count: 0,
	viewer_reaction: null,
	favorited: false,
	can_delete: false,
	recent_comments: [],
});

const suggestion = (
	n: number,
	overrides: Partial<MilestoneSuggestion> = {},
): MilestoneSuggestion => ({
	id: `bbbbbbbb-0000-0000-0000-00000000000${n}`,
	status: "pending",
	source: "ai",
	label: "First steps",
	reason: "Walked across the room",
	model_name: "qwen3:14b",
	source_token_prefix: "",
	created_at: "2026-10-18T01:00:00Z",
	decided_at: null,
	keep: keep(n, `Post ${n}`),
	...overrides,
});

const page = (results: MilestoneSuggestion[]): MilestoneSuggestionPage => ({
	count: results.length,
	next: null,
	previous: null,
	results,
});

function mockLists(
	lists: Partial<Record<ListedSuggestionStatus, MilestoneSuggestion[]>>,
) {
	return vi
		.spyOn(milestoneSuggestionServices, "list")
		.mockImplementation(async (_circleId, { status }) =>
			page(lists[status] ?? []),
		);
}

beforeEach(() => {
	vi.spyOn(circleServices, "listMemberships").mockResolvedValue({
		data: { circles: [] },
	});
});

afterEach(() => {
	vi.restoreAllMocks();
});

describe("MilestoneSuggestionsSection", () => {
	it("stays hidden while nothing is pending", async () => {
		const list = mockLists({});

		const { container } = renderWithQueryClient(
			<MilestoneSuggestionsSection circleId={7} />,
		);

		await waitFor(() =>
			expect(list).toHaveBeenCalledWith(7, { status: "pending", offset: 0 }),
		);
		expect(container).toBeEmptyDOMElement();
	});

	it("lists pending picks with their label and note", async () => {
		mockLists({
			pending: [
				suggestion(1),
				suggestion(2, {
					source: "agent",
					source_token_prefix: "circ_abc1234",
					label: "First haircut",
					reason: "Mentions the first trip to the barber",
				}),
			],
		});

		renderWithQueryClient(<MilestoneSuggestionsSection circleId={7} />);

		const section = await screen.findByRole("region", { name: /Suggested/ });
		expect(within(section).getByText("2")).toBeInTheDocument();
		expect(screen.getByRole("heading", { name: "Post 1" })).toBeInTheDocument();
		expect(screen.getByText("First steps")).toBeInTheDocument();
		expect(screen.getByText("AI note")).toBeInTheDocument();
		expect(screen.getByText(": Walked across the room")).toBeInTheDocument();
		expect(
			screen.getByText("Suggested by API token circ_abc1234"),
		).toBeInTheDocument();
		expect(
			screen.getAllByRole("button", { name: "Add to Milestones" }),
		).toHaveLength(2);
		expect(
			screen.getAllByRole("button", { name: "Dismiss suggestion" }),
		).toHaveLength(2);
	});

	it("shows untrusted text as plain text", async () => {
		const payload = '<img src=x onerror="alert(1)">';
		mockLists({
			pending: [suggestion(1, { label: payload, reason: payload })],
		});

		const { container } = renderWithQueryClient(
			<MilestoneSuggestionsSection circleId={7} />,
		);

		expect(await screen.findByText(payload)).toBeInTheDocument();
		expect(screen.getByText(`: ${payload}`)).toBeInTheDocument();
		expect(container.querySelector("img[onerror]")).toBeNull();
	});

	it("adds a pick to the album", async () => {
		mockLists({ pending: [suggestion(1)] });
		const approve = vi
			.spyOn(milestoneSuggestionServices, "approve")
			.mockResolvedValue({
				suggestion: { ...suggestion(1), status: "approved" },
				album_id: ALBUM_ID,
			});

		renderWithQueryClient(<MilestoneSuggestionsSection circleId={7} />);
		await act(async () =>
			fireEvent.click(
				await screen.findByRole("button", { name: "Add to Milestones" }),
			),
		);

		expect(approve).toHaveBeenCalledWith(7, suggestion(1).id);
	});

	it("dismisses a pick", async () => {
		mockLists({ pending: [suggestion(1)] });
		const dismiss = vi
			.spyOn(milestoneSuggestionServices, "dismiss")
			.mockResolvedValue({
				suggestion: { ...suggestion(1), status: "dismissed", reason: "" },
			});

		renderWithQueryClient(<MilestoneSuggestionsSection circleId={7} />);
		await act(async () =>
			fireEvent.click(
				await screen.findByRole("button", { name: "Dismiss suggestion" }),
			),
		);

		expect(dismiss).toHaveBeenCalledWith(7, suggestion(1).id);
	});

	it("shows dismissed picks, which can still be added", async () => {
		const list = mockLists({
			pending: [suggestion(1)],
			dismissed: [suggestion(2, { status: "dismissed", reason: "" })],
		});

		renderWithQueryClient(<MilestoneSuggestionsSection circleId={7} />);
		fireEvent.click(
			await screen.findByRole("switch", { name: "Show dismissed" }),
		);

		expect(
			await screen.findByRole("heading", { name: "Post 2" }),
		).toBeInTheDocument();
		expect(list).toHaveBeenCalledWith(7, { status: "dismissed", offset: 0 });
		expect(
			screen.getByRole("region", { name: /Dismissed/ }),
		).toBeInTheDocument();
		expect(screen.queryByRole("heading", { name: "Post 1" })).toBeNull();
		expect(
			screen.getByRole("button", { name: "Add to Milestones" }),
		).toBeInTheDocument();
		expect(
			screen.queryByRole("button", { name: "Dismiss suggestion" }),
		).toBeNull();
	});
});
