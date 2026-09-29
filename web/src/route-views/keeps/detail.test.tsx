import "@/i18n/config";
import { renderWithQueryClient } from "@/test-utils";
import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

// Layout pulls in the auth session and router; this suite only cares about the
// post inside it.
vi.mock("@/components", async (importOriginal) => {
	const actual = await importOriginal<typeof import("@/components")>();
	const Layout = Object.assign(
		({ children }: { children?: ReactNode }) => <main>{children}</main>,
		{ Loading: () => <p>Loading…</p> },
	);
	return { ...actual, Layout };
});

const navigate = vi.fn();

vi.mock("@tanstack/react-router", async (importOriginal) => ({
	...(await importOriginal<typeof import("@tanstack/react-router")>()),
	getRouteApi: () => ({
		useParams: () => ({ keepId: "11111111-1111-1111-1111-111111111111" }),
	}),
	useNavigate: () => navigate,
	Link: ({ children, to }: { children?: ReactNode; to: string }) => (
		<a href={to}>{children}</a>
	),
}));

import { type FeedKeep, keepServices } from "@/features/keeps";
import { KeepDetailRouteView } from "./detail";

const keep: FeedKeep = {
	id: "11111111-1111-1111-1111-111111111111",
	circle: { id: 1, name: "Merza Family", slug: "merza-family" },
	created_by: 1,
	created_by_display_name: "Leo",
	title: "Beach day",
	description: "",
	date_of_memory: "2026-07-04T00:00:00Z",
	created_at: "2026-07-04T00:00:00Z",
	media: [],
	reaction_count: 0,
	comment_count: 0,
	viewer_reaction: null,
	favorited: false,
	can_delete: true,
	recent_comments: [],
};

afterEach(() => {
	vi.restoreAllMocks();
	navigate.mockReset();
});

describe("KeepDetailRouteView", () => {
	it("goes back to the feed once the post is deleted", async () => {
		vi.spyOn(keepServices, "getFeedKeep").mockResolvedValue(keep);
		vi.spyOn(keepServices, "getKeepComments").mockResolvedValue({
			count: 0,
			next: null,
			previous: null,
			results: [],
		});
		const deleteKeep = vi
			.spyOn(keepServices, "deleteKeep")
			.mockResolvedValue(undefined);

		renderWithQueryClient(<KeepDetailRouteView />);

		fireEvent.click(await screen.findByRole("button", { name: "Delete post" }));
		expect(navigate).not.toHaveBeenCalled();
		await act(async () =>
			fireEvent.click(await screen.findByRole("button", { name: "Delete" })),
		);

		expect(deleteKeep).toHaveBeenCalledWith(keep.id);
		await waitFor(() => expect(navigate).toHaveBeenCalledWith({ to: "/" }));
	});
});
