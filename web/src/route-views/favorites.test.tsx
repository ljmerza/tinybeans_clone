import "@/i18n/config";
import { renderWithQueryClient } from "@/test-utils";
import { act, fireEvent, screen, waitFor } from "@testing-library/react";
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

import { type FeedKeep, keepServices } from "@/features/keeps";
import { FavoritesRouteView } from "./favorites";

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
	favorited: true,
	can_delete: false,
	recent_comments: [],
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
});

afterEach(() => {
	vi.restoreAllMocks();
});

describe("FavoritesRouteView", () => {
	it("lists favorites and follows the cursor to the next page", async () => {
		const getFavorites = vi
			.spyOn(keepServices, "getFavorites")
			.mockImplementation(async (cursor) =>
				cursor
					? page([keep(2)])
					: page(
							[keep(1)],
							"http://web:8000/api/keeps/feed/favorites/?cursor=abc",
						),
			);

		renderWithQueryClient(<FavoritesRouteView />);

		expect(
			await screen.findByRole("heading", { name: "Memory 1" }),
		).toBeInTheDocument();
		expect(
			await screen.findByRole("heading", { name: "Memory 2" }),
		).toBeInTheDocument();
		expect(getFavorites).toHaveBeenNthCalledWith(1, undefined);
		expect(getFavorites).toHaveBeenNthCalledWith(2, "abc");
		expect(
			await screen.findByText("That's all of your favorites."),
		).toBeInTheDocument();
		expect(
			screen.getByRole("feed", { name: "Your favorite posts" }),
		).toBeInTheDocument();
	});

	it("shows an empty state", async () => {
		vi.spyOn(keepServices, "getFavorites").mockResolvedValue(page([]));

		renderWithQueryClient(<FavoritesRouteView />);

		expect(await screen.findByText("No favorites yet")).toBeInTheDocument();
	});

	it("keeps an unfavorited post in place, unfilled, until the next visit", async () => {
		vi.spyOn(keepServices, "getFavorites").mockResolvedValue(page([keep(1)]));
		vi.spyOn(keepServices, "unfavoriteKeep").mockResolvedValue(undefined);

		renderWithQueryClient(<FavoritesRouteView />);
		const button = await screen.findByRole("button", {
			name: "Remove from favorites",
		});
		await act(async () => fireEvent.click(button));

		expect(
			await screen.findByRole("button", { name: "Add to favorites" }),
		).toHaveAttribute("aria-pressed", "false");
		expect(
			screen.getByRole("heading", { name: "Memory 1" }),
		).toBeInTheDocument();
	});

	it("refetches on every visit, so deleted posts drop off", async () => {
		const getFavorites = vi
			.spyOn(keepServices, "getFavorites")
			.mockResolvedValue(page([keep(1), keep(2)]));

		const { queryClient, unmount } = renderWithQueryClient(
			<FavoritesRouteView />,
		);
		expect(
			await screen.findByRole("heading", { name: "Memory 2" }),
		).toBeInTheDocument();
		unmount();

		// Memory 2 was deleted while the user was elsewhere.
		getFavorites.mockResolvedValue(page([keep(1)]));
		renderWithQueryClient(<FavoritesRouteView />, { queryClient });

		await waitFor(() =>
			expect(screen.queryByRole("heading", { name: "Memory 2" })).toBeNull(),
		);
		expect(
			screen.getByRole("heading", { name: "Memory 1" }),
		).toBeInTheDocument();
		expect(getFavorites).toHaveBeenCalledTimes(2);
	});

	it("drops a post that was deleted in the meantime when it is toggled", async () => {
		vi.spyOn(keepServices, "getFavorites").mockResolvedValue(
			page([keep(1), keep(2)]),
		);
		const unfavoriteKeep = vi
			.spyOn(keepServices, "unfavoriteKeep")
			.mockRejectedValue(notFound());

		renderWithQueryClient(<FavoritesRouteView />);
		await screen.findByRole("heading", { name: "Memory 2" });
		const buttons = screen.getAllByRole("button", {
			name: "Remove from favorites",
		});
		await act(async () => fireEvent.click(buttons[1] as HTMLElement));

		expect(unfavoriteKeep).toHaveBeenCalledWith(keep(2).id);
		await waitFor(() =>
			expect(screen.queryByRole("heading", { name: "Memory 2" })).toBeNull(),
		);
		expect(
			screen.getByRole("heading", { name: "Memory 1" }),
		).toBeInTheDocument();
	});
});
