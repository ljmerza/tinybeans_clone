import "@/i18n/config";
import { renderWithQueryClient } from "@/test-utils";
import { screen, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Layout pulls in the auth session and router; this suite only cares about the
// list inside it.
vi.mock("@/components", async (importOriginal) => {
	const actual = await importOriginal<typeof import("@/components")>();
	const Layout = ({ children }: { children?: ReactNode }) => (
		<main>{children}</main>
	);
	Layout.Loading = ({ message }: { message?: string }) => <p>{message}</p>;
	Layout.Error = ({ title }: { title?: string }) => <p>{title}</p>;
	return { ...actual, Layout };
});

const search: { child?: string } = {};

vi.mock("@tanstack/react-router", async (importOriginal) => ({
	...(await importOriginal<typeof import("@tanstack/react-router")>()),
	getRouteApi: () => ({ useSearch: () => search }),
	Link: ({
		children,
		to,
		search: params,
		...props
	}: {
		children?: ReactNode;
		to: string;
		search?: Record<string, string>;
	}) => (
		<a href={`${to}?${new URLSearchParams(params)}`} {...props}>
			{children}
		</a>
	),
}));

import { type FeedKeep, type KeepChild, keepServices } from "@/features/keeps";
import { MilestonesRouteView } from "./milestones";

const EMMA = "22222222-2222-2222-2222-222222222222";
const LIAM = "33333333-3333-3333-3333-333333333333";

const keep = (n: number): FeedKeep => ({
	id: `00000000-0000-0000-0000-00000000000${n}`,
	circle: { id: 1, name: "Family", slug: "family" },
	created_by: 1,
	created_by_display_name: "Leo",
	title: `Milestone ${n}`,
	description: "",
	date_of_memory: "2026-07-04T00:00:00Z",
	created_at: "2026-07-04T00:00:00Z",
	media: [],
	reaction_count: 0,
	comment_count: 0,
	viewer_reaction: null,
	favorited: false,
	can_delete: false,
	recent_comments: [],
	milestone: {
		milestone_type: "first_steps",
		child: { id: EMMA, display_name: "Emma" },
		child_age: null,
		age_at_milestone: "",
	},
});

const child = (id: string, name: string, count: number): KeepChild => ({
	id,
	display_name: name,
	circle: { id: 1, name: "Family", slug: "family" },
	milestone_count: count,
});

const page = (results: FeedKeep[], next: string | null = null) => ({
	next,
	previous: null,
	results,
});

beforeEach(() => {
	// jsdom has no scrolling; the window virtualizer calls this on mount.
	vi.spyOn(window, "scrollTo").mockImplementation(() => {});
	vi.spyOn(keepServices, "getChildren").mockResolvedValue([]);
});

afterEach(() => {
	vi.restoreAllMocks();
	search.child = undefined;
});

describe("MilestonesRouteView", () => {
	it("lists milestones in order and follows the cursor", async () => {
		const getMilestones = vi
			.spyOn(keepServices, "getMilestones")
			.mockImplementation(async (cursor) =>
				cursor
					? page([keep(2)])
					: page(
							[keep(1)],
							"http://web:8000/api/keeps/feed/milestones/?cursor=abc",
						),
			);

		renderWithQueryClient(<MilestonesRouteView />);

		const feed = await screen.findByRole("feed", { name: "Milestones" });
		expect(
			await within(feed).findByRole("heading", { name: "Milestone 2" }),
		).toBeInTheDocument();
		const headings = within(feed)
			.getAllByRole("heading")
			.map((heading) => heading.textContent);
		expect(headings).toEqual(["Milestone 1", "Milestone 2"]);
		expect(getMilestones).toHaveBeenNthCalledWith(1, undefined, undefined);
		expect(getMilestones).toHaveBeenNthCalledWith(2, "abc", undefined);
		expect(
			await screen.findByText("That's every milestone so far."),
		).toBeInTheDocument();
		// No page title, and no child picker without children.
		expect(screen.queryByRole("heading", { level: 1 })).toBeNull();
		expect(screen.queryByRole("navigation")).toBeNull();
	});

	it("filters to the child in the URL and offers the children with milestones", async () => {
		search.child = LIAM;
		vi.mocked(keepServices.getChildren).mockResolvedValue([
			child(EMMA, "Emma", 2),
			child(LIAM, "Liam", 1),
			child("44444444-4444-4444-4444-444444444444", "Noah", 0),
		]);
		const getMilestones = vi
			.spyOn(keepServices, "getMilestones")
			.mockResolvedValue(page([keep(1)]));

		renderWithQueryClient(<MilestonesRouteView />);

		const picker = await screen.findByRole("navigation", {
			name: "Whose milestones",
		});
		const links = within(picker).getAllByRole("link");
		expect(links.map((link) => link.textContent)).toEqual([
			"Everyone",
			"Emma",
			"Liam",
		]);
		expect(links[0]).toHaveAttribute("href", "/milestones?");
		expect(links[2]).toHaveAttribute("href", `/milestones?child=${LIAM}`);
		expect(links[2]).toHaveAttribute("aria-current", "page");
		expect(links[0]).not.toHaveAttribute("aria-current");
		expect(getMilestones).toHaveBeenCalledWith(undefined, LIAM);
	});

	it("has no picker with only one child to show", async () => {
		vi.mocked(keepServices.getChildren).mockResolvedValue([
			child(EMMA, "Emma", 2),
		]);
		vi.spyOn(keepServices, "getMilestones").mockResolvedValue(page([keep(1)]));

		renderWithQueryClient(<MilestonesRouteView />);

		await screen.findByRole("heading", { name: "Milestone 1" });
		expect(screen.queryByRole("navigation")).toBeNull();
	});

	it("shows an empty state", async () => {
		vi.spyOn(keepServices, "getMilestones").mockResolvedValue(page([]));

		renderWithQueryClient(<MilestonesRouteView />);

		expect(
			await screen.findByRole("heading", { name: "No milestones yet" }),
		).toBeInTheDocument();
	});
});
