import "@/i18n/config";
import { renderWithQueryClient } from "@/test-utils";
import { screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Layout pulls in the auth session and router; this suite only cares about the
// feed inside it.
vi.mock("@/components", async (importOriginal) => {
	const actual = await importOriginal<typeof import("@/components")>();
	const Layout = Object.assign(
		({ children }: { children?: ReactNode }) => <main>{children}</main>,
		{ Loading: ({ message }: { message?: string }) => <p>{message}</p> },
	);
	return { ...actual, Layout };
});

const PERSON_ID = "bbbbbbbb-0000-0000-0000-000000000001";

vi.mock("@tanstack/react-router", async (importOriginal) => ({
	...(await importOriginal<typeof import("@tanstack/react-router")>()),
	getRouteApi: () => ({ useParams: () => ({ personId: PERSON_ID }) }),
	Link: ({
		children,
		to,
		params,
		...props
	}: {
		children?: ReactNode;
		to: string;
		params?: { personId: string };
		"aria-label"?: string;
	}) => (
		<a
			href={to.replace("$personId", params?.personId ?? "")}
			aria-label={props["aria-label"]}
		>
			{children}
		</a>
	),
}));

import { type FeedKeep, keepServices } from "@/features/keeps";
import { PersonRouteView } from "./detail";

const sophia = { id: PERSON_ID, name: "Sophia M" };

const keep = (n: number): FeedKeep => ({
	id: `00000000-0000-0000-0000-00000000000${n}`,
	circle: { id: 1, name: "Family", slug: "family" },
	created_by: 1,
	created_by_display_name: "Leo",
	title: `Memory ${n}`,
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
	people: [sophia],
});

const page = (results: FeedKeep[], next: string | null = null) => ({
	next,
	previous: null,
	results,
});

const notFound = () => Object.assign(new Error("Not found."), { status: 404 });

beforeEach(() => {
	// jsdom has no scrolling; the window virtualizer calls this on mount.
	vi.spyOn(window, "scrollTo").mockImplementation(() => {});
	vi.spyOn(keepServices, "getPerson").mockResolvedValue({
		...sophia,
		kind: "child",
		circle: { id: 1, name: "Family", slug: "family" },
	});
});

afterEach(() => {
	vi.restoreAllMocks();
});

describe("PersonRouteView", () => {
	it("lists the person's posts and follows the cursor", async () => {
		const getPersonFeed = vi
			.spyOn(keepServices, "getPersonFeed")
			.mockImplementation(async (_personId, cursor) =>
				cursor
					? page([keep(2)])
					: page([keep(1)], "http://web:8000/api/keeps/feed/?cursor=abc"),
			);

		renderWithQueryClient(<PersonRouteView />);

		expect(
			await screen.findByRole("heading", { level: 1, name: "Sophia M" }),
		).toBeInTheDocument();
		expect(screen.getByText("· Family")).toBeInTheDocument();
		expect(
			await screen.findByRole("heading", { name: "Memory 1" }),
		).toBeInTheDocument();
		expect(
			await screen.findByRole("heading", { name: "Memory 2" }),
		).toBeInTheDocument();
		expect(getPersonFeed).toHaveBeenNthCalledWith(1, PERSON_ID, undefined);
		expect(getPersonFeed).toHaveBeenNthCalledWith(2, PERSON_ID, "abc");
		expect(
			await screen.findByText("That's every post with Sophia M."),
		).toBeInTheDocument();
		expect(
			screen.getByRole("feed", { name: "Posts with Sophia M" }),
		).toBeInTheDocument();
		// Each post links back to the person.
		expect(
			screen.getAllByRole("link", { name: "Sophia M" })[0],
		).toHaveAttribute("href", `/people/${PERSON_ID}`);
		expect(
			screen.getByRole("link", { name: "Back to the feed" }),
		).toHaveAttribute("href", "/");
	});

	it("shows an empty state", async () => {
		vi.spyOn(keepServices, "getPersonFeed").mockResolvedValue(page([]));

		renderWithQueryClient(<PersonRouteView />);

		expect(await screen.findByText("No posts yet")).toBeInTheDocument();
		expect(
			screen.getByText("Posts Sophia M is tagged in show up here."),
		).toBeInTheDocument();
	});

	it("says so when the person isn't visible", async () => {
		vi.mocked(keepServices.getPerson).mockRejectedValue(notFound());
		vi.spyOn(keepServices, "getPersonFeed").mockResolvedValue(page([]));

		renderWithQueryClient(<PersonRouteView />);

		expect(await screen.findByText("Person not found")).toBeInTheDocument();
	});
});
