import "@/i18n/config";
import { renderWithQueryClient } from "@/test-utils";
import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Layout pulls in the auth session and router; this suite only cares about the
// album inside it.
vi.mock("@/components", async (importOriginal) => {
	const actual = await importOriginal<typeof import("@/components")>();
	const Layout = Object.assign(
		({ children }: { children?: ReactNode }) => <main>{children}</main>,
		{ Loading: ({ message }: { message?: string }) => <p>{message}</p> },
	);
	return { ...actual, Layout };
});

const navigate = vi.fn();
const ALBUM_ID = "aaaaaaaa-0000-0000-0000-000000000001";

vi.mock("@tanstack/react-router", async (importOriginal) => ({
	...(await importOriginal<typeof import("@tanstack/react-router")>()),
	getRouteApi: () => ({ useParams: () => ({ albumId: ALBUM_ID }) }),
	useNavigate: () => navigate,
	Link: ({
		children,
		to,
		...props
	}: { children?: ReactNode; to: string; "aria-label"?: string }) => (
		<a href={to} aria-label={props["aria-label"]}>
			{children}
		</a>
	),
}));

import { albumKeys, albumServices } from "@/features/albums";
import { albumPage, makeAlbum } from "@/features/albums/testData";
import { circleServices } from "@/features/circles";
import type { FeedKeep } from "@/features/keeps";
import type { HttpError } from "@/lib/httpClient";
import { createTestQueryClient } from "@/lib/query/queryClient";
import { toast } from "sonner";
import { AlbumRouteView } from "./detail";

const keep = (n: number): FeedKeep => ({
	id: `00000000-0000-0000-0000-00000000000${n}`,
	circle: { id: 7, name: "Family", slug: "family" },
	created_by: 1,
	created_by_display_name: "Leo",
	title: `Day ${n}`,
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

/** A post with one photo, so it can be an album's cover. */
const photoKeep = (n: number): FeedKeep => ({
	...keep(n),
	media: [
		{
			id: n,
			media_type: "photo",
			url: `/media/${n}.jpg`,
			poster_url: null,
			width: 800,
			height: 600,
			caption: "",
		},
	],
});

const coverOf = (n: number) => ({
	keep_id: keep(n).id,
	media_type: "photo" as const,
	url: `/media/${n}.jpg`,
});

const notFound = () =>
	Object.assign(new Error("Not found."), { status: 404 }) as HttpError;

beforeEach(() => {
	// jsdom has no scrolling; the window virtualizer calls this on mount.
	vi.spyOn(window, "scrollTo").mockImplementation(() => {});
});

afterEach(() => {
	vi.restoreAllMocks();
	navigate.mockReset();
});

describe("AlbumRouteView", () => {
	it("shows the album's name and its posts, following the cursor", async () => {
		vi.spyOn(albumServices, "get").mockResolvedValue(
			makeAlbum({ id: ALBUM_ID, post_count: 2, can_edit: false }),
		);
		const getKeeps = vi
			.spyOn(albumServices, "getKeeps")
			.mockImplementation(async (_id, cursor) =>
				cursor
					? { next: null, previous: null, results: [keep(2)] }
					: {
							next: `http://web:8000/api/albums/${ALBUM_ID}/keeps/?cursor=abc`,
							previous: null,
							results: [keep(1)],
						},
			);

		renderWithQueryClient(<AlbumRouteView />);

		expect(
			await screen.findByRole("heading", { level: 1, name: "Beach trip 2026" }),
		).toBeInTheDocument();
		expect(screen.getByText(/2 posts/)).toBeInTheDocument();
		expect(
			await screen.findByRole("heading", { name: "Day 1" }),
		).toBeInTheDocument();
		expect(
			await screen.findByRole("heading", { name: "Day 2" }),
		).toBeInTheDocument();
		expect(getKeeps).toHaveBeenNthCalledWith(1, ALBUM_ID, undefined);
		expect(getKeeps).toHaveBeenNthCalledWith(2, ALBUM_ID, "abc");
		expect(
			screen.getByRole("feed", { name: "Posts in Beach trip 2026" }),
		).toBeInTheDocument();
		expect(screen.getByRole("link", { name: "All albums" })).toHaveAttribute(
			"href",
			"/albums",
		);
		// Only its creator or a circle admin may change it.
		expect(screen.queryByRole("button", { name: "Edit album" })).toBeNull();
		expect(screen.queryByRole("button", { name: "Delete album" })).toBeNull();
	});

	it("shows an empty state", async () => {
		vi.spyOn(albumServices, "get").mockResolvedValue(
			makeAlbum({ id: ALBUM_ID }),
		);
		vi.spyOn(albumServices, "getKeeps").mockResolvedValue({
			next: null,
			previous: null,
			results: [],
		});

		renderWithQueryClient(<AlbumRouteView />);

		expect(await screen.findByText("This album is empty")).toBeInTheDocument();
	});

	it("lets its creator rename it", async () => {
		const album = makeAlbum({ id: ALBUM_ID, can_edit: true });
		vi.spyOn(albumServices, "get").mockResolvedValue(album);
		vi.spyOn(albumServices, "getKeeps").mockResolvedValue({
			next: null,
			previous: null,
			results: [],
		});
		vi.spyOn(circleServices, "listMemberships").mockResolvedValue({
			data: { circles: [] },
		});
		const update = vi
			.spyOn(albumServices, "update")
			.mockResolvedValue({ ...album, name: "Beach week" });

		renderWithQueryClient(<AlbumRouteView />);
		fireEvent.click(await screen.findByRole("button", { name: "Edit album" }));
		fireEvent.change(await screen.findByLabelText("Name"), {
			target: { value: "Beach week" },
		});
		await act(async () =>
			fireEvent.click(screen.getByRole("button", { name: "Save" })),
		);

		expect(update).toHaveBeenCalledWith(ALBUM_ID, {
			name: "Beach week",
			description: "",
		});
		expect(
			await screen.findByRole("heading", { level: 1, name: "Beach week" }),
		).toBeInTheDocument();
	});

	it("goes back to the albums once it is deleted", async () => {
		vi.spyOn(albumServices, "get").mockResolvedValue(
			makeAlbum({ id: ALBUM_ID, can_edit: true }),
		);
		vi.spyOn(albumServices, "getKeeps").mockResolvedValue({
			next: null,
			previous: null,
			results: [keep(1)],
		});
		const remove = vi
			.spyOn(albumServices, "delete")
			.mockResolvedValue(undefined);

		renderWithQueryClient(<AlbumRouteView />);
		fireEvent.click(
			await screen.findByRole("button", { name: "Delete album" }),
		);
		expect(
			await screen.findByText(
				"The album goes away for everyone in the circle. Its posts stay.",
			),
		).toBeInTheDocument();
		const confirm = screen
			.getAllByRole("button", { name: "Delete album" })
			.at(-1) as HTMLElement;
		await act(async () => fireEvent.click(confirm));

		expect(remove).toHaveBeenCalledWith(ALBUM_ID);
		await waitFor(() =>
			expect(navigate).toHaveBeenCalledWith({ to: "/albums" }),
		);
	});

	it("says so when the album is gone", async () => {
		vi.spyOn(albumServices, "get").mockRejectedValue(notFound());
		vi.spyOn(albumServices, "getKeeps").mockRejectedValue(notFound());

		renderWithQueryClient(<AlbumRouteView />);

		expect(await screen.findByText("Album not found")).toBeInTheDocument();
	});

	describe("cover picker", () => {
		const coverButton = async (name: string) =>
			screen.findByRole("button", { name });

		function renderAlbum(
			albumOverrides: Parameters<typeof makeAlbum>[0],
			keeps: FeedKeep[] = [photoKeep(1), photoKeep(2), keep(3)],
		) {
			vi.spyOn(albumServices, "get").mockResolvedValue(
				makeAlbum({
					id: ALBUM_ID,
					post_count: keeps.length,
					...albumOverrides,
				}),
			);
			vi.spyOn(albumServices, "getKeeps").mockResolvedValue({
				next: null,
				previous: null,
				results: keeps,
			});
			vi.spyOn(circleServices, "listMemberships").mockResolvedValue({
				data: { circles: [] },
			});
			// Keep the albums list cached without an observer, as after a visit.
			const queryClient = createTestQueryClient({
				defaultOptions: { queries: { gcTime: Number.POSITIVE_INFINITY } },
			});
			return renderWithQueryClient(<AlbumRouteView />, { queryClient });
		}

		it("lets an admin make a post the cover, marking the current one", async () => {
			const album = makeAlbum({
				id: ALBUM_ID,
				can_edit: true,
				post_count: 3,
				cover: coverOf(1),
			});
			const update = vi.spyOn(albumServices, "update").mockResolvedValue({
				...album,
				cover_keep: keep(2).id,
				cover: coverOf(2),
			});
			const { queryClient } = renderAlbum({
				can_edit: true,
				cover: coverOf(1),
			});
			queryClient.setQueryData(albumKeys.list(), {
				pages: [albumPage([album])],
				pageParams: [0],
			});

			// The first post is the cover by default; nothing to reset.
			const current = await coverButton("Album cover (default)");
			expect(current).toHaveAttribute("data-active");
			expect(current).toHaveAttribute("aria-disabled", "true");
			fireEvent.click(current);
			expect(update).not.toHaveBeenCalled();
			// A text-only post can't be a cover.
			expect(
				screen.getAllByRole("button", { name: /album cover/i }),
			).toHaveLength(2);

			await act(async () =>
				fireEvent.click(await coverButton("Set as album cover")),
			);

			expect(update).toHaveBeenCalledWith(ALBUM_ID, {
				cover_keep: keep(2).id,
			});
			expect(await coverButton("Use the default album cover")).toHaveAttribute(
				"data-active",
			);
			expect(await coverButton("Set as album cover")).not.toHaveAttribute(
				"data-active",
			);
			const list = queryClient.getQueryData<{
				pages: { results: { cover: unknown }[] }[];
			}>(albumKeys.list());
			expect(list?.pages[0].results[0].cover).toEqual(coverOf(2));
		});

		it("lets an admin go back to the default cover", async () => {
			const album = makeAlbum({
				id: ALBUM_ID,
				can_edit: true,
				post_count: 3,
				cover_keep: keep(2).id,
				cover: coverOf(2),
			});
			const update = vi
				.spyOn(albumServices, "update")
				.mockResolvedValue({ ...album, cover_keep: null, cover: coverOf(1) });
			renderAlbum({
				can_edit: true,
				cover_keep: keep(2).id,
				cover: coverOf(2),
			});

			await act(async () =>
				fireEvent.click(await coverButton("Use the default album cover")),
			);

			expect(update).toHaveBeenCalledWith(ALBUM_ID, { cover_keep: null });
			expect(await coverButton("Album cover (default)")).toHaveAttribute(
				"data-active",
			);
		});

		it("says so when changing the cover fails", async () => {
			vi.spyOn(albumServices, "update").mockRejectedValue(
				Object.assign(new Error("Server error"), { status: 500 }),
			);
			const error = vi.spyOn(toast, "error");
			renderAlbum({ can_edit: true, cover: coverOf(1) });

			await act(async () =>
				fireEvent.click(await coverButton("Set as album cover")),
			);

			await waitFor(() =>
				expect(error).toHaveBeenCalledWith(
					"Couldn't change the album cover. Please try again.",
					expect.anything(),
				),
			);
			expect(await coverButton("Album cover (default)")).toBeInTheDocument();
		});

		it("isn't offered to members who can't edit the album", async () => {
			renderAlbum({ can_edit: false, cover: coverOf(1) });

			expect(
				await screen.findByRole("heading", { name: "Day 1" }),
			).toBeInTheDocument();
			expect(screen.queryByRole("button", { name: /album cover/i })).toBeNull();
		});
	});
});
