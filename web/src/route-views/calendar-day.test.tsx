import "@/i18n/config";
import { renderWithQueryClient } from "@/test-utils";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Layout pulls in the auth session and router; this suite only cares about the
// day feed inside it.
vi.mock("@/components", async (importOriginal) => {
	const actual = await importOriginal<typeof import("@/components")>();
	const Layout = ({ children }: { children?: ReactNode }) => (
		<main>{children}</main>
	);
	return { ...actual, Layout };
});

const navigate = vi.fn();
const routeState = vi.hoisted(() => ({
	params: { date: "2026-07-04" },
	search: { circle: "family" as string | undefined },
}));

vi.mock("@tanstack/react-router", async (importOriginal) => ({
	...(await importOriginal<typeof import("@tanstack/react-router")>()),
	getRouteApi: () => ({
		useParams: () => routeState.params,
		useSearch: () => routeState.search,
	}),
	useNavigate: () => navigate,
	Link: ({
		children,
		search,
		className,
	}: {
		children?: ReactNode;
		search: { month: string; circle?: string };
		className?: string;
	}) => (
		<a
			href={`/calendar?month=${search.month}&circle=${search.circle}`}
			className={className}
		>
			{children}
		</a>
	),
}));

import { type FeedKeep, keepServices } from "@/features/keeps";
import { CalendarDayRouteView } from "./calendar-day";

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
	recent_comments: [],
});

beforeEach(() => {
	// jsdom has no scrolling; the window virtualizer calls this on mount.
	vi.spyOn(window, "scrollTo").mockImplementation(() => {});
});

afterEach(() => {
	vi.restoreAllMocks();
	navigate.mockReset();
});

describe("CalendarDayRouteView", () => {
	it("shows the day's posts for the selected circle", async () => {
		const getFeed = vi.spyOn(keepServices, "getFeed").mockResolvedValue({
			next: null,
			previous: null,
			results: [keep(1), keep(2)],
		});
		vi.spyOn(keepServices, "getAdjacentFeedDays").mockResolvedValue({
			date: "2026-07-04",
			previous: null,
			next: null,
		});

		renderWithQueryClient(<CalendarDayRouteView />);

		expect(
			await screen.findByRole("heading", { name: "Memory 1" }),
		).toBeInTheDocument();
		expect(
			screen.getByRole("heading", { name: "Memory 2" }),
		).toBeInTheDocument();
		expect(getFeed).toHaveBeenCalledWith(undefined, {
			date: "2026-07-04",
			circleSlug: "family",
		});
		expect(
			screen.getByRole("heading", { level: 1, name: /July 4, 2026/ }),
		).toBeInTheDocument();
		expect(screen.getByRole("link", { name: "Back to July" })).toHaveAttribute(
			"href",
			"/calendar?month=2026-07&circle=family",
		);
	});

	it("arrows jump to the nearest days with photos", async () => {
		vi.spyOn(keepServices, "getFeed").mockResolvedValue({
			next: null,
			previous: null,
			results: [keep(1)],
		});
		const getAdjacent = vi
			.spyOn(keepServices, "getAdjacentFeedDays")
			.mockResolvedValue({
				date: "2026-07-04",
				previous: "2026-06-28",
				next: null,
			});

		renderWithQueryClient(<CalendarDayRouteView />);

		const previous = screen.getByRole("button", {
			name: "Previous day with photos",
		});
		await waitFor(() => expect(previous).toBeEnabled());
		expect(getAdjacent).toHaveBeenCalledWith("2026-07-04", "family");
		expect(
			screen.getByRole("button", { name: "Next day with photos" }),
		).toBeDisabled();

		fireEvent.click(previous);

		expect(navigate).toHaveBeenCalledWith({
			to: "/calendar/$date",
			params: { date: "2026-06-28" },
			search: { circle: "family" },
		});
	});

	it("says so when the day has no photos", async () => {
		vi.spyOn(keepServices, "getFeed").mockResolvedValue({
			next: null,
			previous: null,
			results: [],
		});
		vi.spyOn(keepServices, "getAdjacentFeedDays").mockResolvedValue({
			date: "2026-07-04",
			previous: null,
			next: null,
		});

		renderWithQueryClient(<CalendarDayRouteView />);

		expect(
			await screen.findByRole("heading", { name: "No photos on this day" }),
		).toBeInTheDocument();
	});
});
