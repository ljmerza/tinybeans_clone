import "@/i18n/config";
import { renderWithQueryClient } from "@/test-utils";
import { act, fireEvent, screen, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Layout pulls in the auth session and router; this suite only cares about the
// albums inside it.
vi.mock("@/components", async (importOriginal) => {
	const actual = await importOriginal<typeof import("@/components")>();
	const Layout = ({ children }: { children?: ReactNode }) => (
		<main>{children}</main>
	);
	Layout.Loading = ({ message }: { message?: string }) => <p>{message}</p>;
	Layout.Error = ({ title }: { title?: string }) => <p>{title}</p>;
	return { ...actual, Layout };
});

const navigate = vi.fn();

vi.mock("@tanstack/react-router", async (importOriginal) => ({
	...(await importOriginal<typeof import("@tanstack/react-router")>()),
	useNavigate: () => navigate,
	Link: ({
		children,
		to,
		params,
	}: {
		children?: ReactNode;
		to: string;
		params?: { albumId?: string };
	}) => <a href={to.replace("$albumId", params?.albumId ?? "")}>{children}</a>,
}));

import { albumServices } from "@/features/albums";
import { albumPage, makeAlbum } from "@/features/albums/testData";
import { circleServices } from "@/features/circles";
import { AlbumsRouteView } from "./index";

const beach = makeAlbum({
	id: "aaaaaaaa-0000-0000-0000-000000000001",
	name: "Beach trip 2026",
	post_count: 12,
	cover: {
		keep_id: "k1",
		media_type: "photo",
		url: "https://cdn.test/beach.jpg",
	},
});
const xmas = makeAlbum({
	id: "aaaaaaaa-0000-0000-0000-000000000002",
	name: "Christmas",
	post_count: 1,
});

beforeEach(() => {
	vi.spyOn(circleServices, "listMemberships").mockResolvedValue({
		data: {
			circles: [
				{
					membership_id: 1,
					circle: { id: 7, name: "Family", slug: "family", member_count: 2 },
					role: "member",
					is_owner: false,
					created_at: "2026-01-01T00:00:00Z",
				},
			],
		},
	});
});

afterEach(() => {
	vi.restoreAllMocks();
	navigate.mockReset();
});

describe("AlbumsRouteView", () => {
	it("shows a card per album with its cover, name and count", async () => {
		vi.spyOn(albumServices, "list").mockResolvedValue(albumPage([beach, xmas]));

		renderWithQueryClient(<AlbumsRouteView />);

		const grid = await screen.findByRole("list", { name: "Albums" });
		const cards = within(grid).getAllByRole("link");
		expect(cards.map((card) => card.getAttribute("href"))).toEqual([
			`/albums/${beach.id}`,
			`/albums/${xmas.id}`,
		]);
		expect(cards[0]).toHaveTextContent("Beach trip 2026");
		expect(cards[0]).toHaveTextContent("12 posts");
		expect(cards[0]?.querySelector("img")).toHaveAttribute(
			"src",
			"https://cdn.test/beach.jpg",
		);
		expect(cards[1]).toHaveTextContent("1 post");
		// One circle, so no circle names; and no page title.
		expect(cards[0]).not.toHaveTextContent("Family");
		expect(screen.queryByRole("heading")).toBeNull();
	});

	it("names each album's circle when they span several", async () => {
		vi.spyOn(albumServices, "list").mockResolvedValue(
			albumPage([
				beach,
				{ ...xmas, circle: { id: 9, name: "Cousins", slug: "cousins" } },
			]),
		);

		renderWithQueryClient(<AlbumsRouteView />);

		expect(await screen.findByText("12 posts · Family")).toBeInTheDocument();
		expect(screen.getByText("1 post · Cousins")).toBeInTheDocument();
	});

	it("loads more albums on demand", async () => {
		const list = vi
			.spyOn(albumServices, "list")
			.mockImplementation(async ({ offset } = {}) =>
				offset
					? albumPage([xmas])
					: albumPage(
							[beach],
							"http://web:8000/api/albums/?limit=50&offset=50",
						),
			);

		renderWithQueryClient(<AlbumsRouteView />);
		await act(async () =>
			fireEvent.click(await screen.findByRole("button", { name: "Show more" })),
		);

		expect(await screen.findByText("Christmas")).toBeInTheDocument();
		expect(list).toHaveBeenLastCalledWith({ offset: 50 });
		expect(screen.queryByRole("button", { name: "Show more" })).toBeNull();
	});

	it("offers to create the first album and opens it", async () => {
		vi.spyOn(albumServices, "list").mockResolvedValue(albumPage([]));
		const created = makeAlbum({ id: "aaaaaaaa-0000-0000-0000-000000000009" });
		vi.spyOn(albumServices, "create").mockResolvedValue(created);

		renderWithQueryClient(<AlbumsRouteView />);

		expect(await screen.findByText("No albums yet")).toBeInTheDocument();
		fireEvent.click(screen.getByRole("button", { name: "New album" }));
		fireEvent.change(await screen.findByLabelText("Name"), {
			target: { value: "Beach trip 2026" },
		});
		await act(async () =>
			fireEvent.click(screen.getByRole("button", { name: "Create album" })),
		);

		expect(navigate).toHaveBeenCalledWith({
			to: "/albums/$albumId",
			params: { albumId: created.id },
		});
	});
});
