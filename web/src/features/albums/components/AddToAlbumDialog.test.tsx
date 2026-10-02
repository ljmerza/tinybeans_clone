import "@/i18n/config";
import { type FeedKeep, KeepFeedPost } from "@/features/keeps";
import { renderWithQueryClient } from "@/test-utils";
import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { albumServices } from "../api/services";
import { albumPage, makeAlbum } from "../testData";
import { AddToAlbumDialog } from "./AddToAlbumDialog";

const keep: FeedKeep = {
	id: "11111111-1111-1111-1111-111111111111",
	circle: { id: 7, name: "Family", slug: "family" },
	created_by: 1,
	created_by_display_name: "Leo",
	title: "Sandcastle",
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
};

const beach = makeAlbum({
	id: "aaaaaaaa-0000-0000-0000-000000000001",
	name: "Beach trip",
	post_count: 3,
	has_keep: true,
});
const summer = makeAlbum({
	id: "aaaaaaaa-0000-0000-0000-000000000002",
	name: "Summer",
	post_count: 1,
	has_keep: false,
});

function renderDialog() {
	const onOpenChange = vi.fn();
	renderWithQueryClient(
		<AddToAlbumDialog keep={keep} open onOpenChange={onOpenChange} />,
	);
	return { onOpenChange };
}

afterEach(() => {
	vi.restoreAllMocks();
});

describe("AddToAlbumDialog", () => {
	it("lists the circle's albums, checked when the post is in them", async () => {
		const list = vi
			.spyOn(albumServices, "list")
			.mockResolvedValue(albumPage([beach, summer]));

		renderDialog();

		expect(
			await screen.findByRole("checkbox", { name: /Beach trip/ }),
		).toBeChecked();
		expect(screen.getByRole("checkbox", { name: /Summer/ })).not.toBeChecked();
		expect(screen.getByText("3 posts")).toBeInTheDocument();
		expect(screen.getByText("1 post")).toBeInTheDocument();
		expect(screen.getByText(/Albums in Family/)).toBeInTheDocument();
		expect(list).toHaveBeenCalledWith({ keep: keep.id, limit: 200 });
	});

	it("adds and removes the post as boxes are ticked", async () => {
		vi.spyOn(albumServices, "list").mockResolvedValue(
			albumPage([beach, summer]),
		);
		const add = vi
			.spyOn(albumServices, "addKeep")
			.mockResolvedValue({ in_album: true });
		const remove = vi
			.spyOn(albumServices, "removeKeep")
			.mockResolvedValue(undefined);

		renderDialog();
		const summerBox = await screen.findByRole("checkbox", { name: /Summer/ });
		await act(async () => fireEvent.click(summerBox));
		await act(async () =>
			fireEvent.click(screen.getByRole("checkbox", { name: /Beach trip/ })),
		);

		expect(add).toHaveBeenCalledWith(summer.id, keep.id);
		expect(remove).toHaveBeenCalledWith(beach.id, keep.id);
		await waitFor(() => expect(summerBox).toBeChecked());
		expect(
			screen.getByRole("checkbox", { name: /Beach trip/ }),
		).not.toBeChecked();
		// Summer went from 1 to 2 posts, Beach trip from 3 to 2.
		expect(screen.getAllByText("2 posts")).toHaveLength(2);
	});

	it("unticks the box again when adding fails", async () => {
		vi.spyOn(albumServices, "list").mockResolvedValue(albumPage([summer]));
		vi.spyOn(albumServices, "addKeep").mockRejectedValue(new Error("down"));

		renderDialog();
		const box = await screen.findByRole("checkbox", { name: /Summer/ });
		await act(async () => fireEvent.click(box));

		await waitFor(() => expect(box).not.toBeChecked());
		expect(box).toBeEnabled();
	});

	it("starts a new album with the post in it", async () => {
		vi.spyOn(albumServices, "list").mockResolvedValue(albumPage([]));
		const created = makeAlbum({
			id: "aaaaaaaa-0000-0000-0000-000000000003",
			name: "Grandma's visit",
			post_count: 1,
		});
		const create = vi.spyOn(albumServices, "create").mockResolvedValue(created);

		renderDialog();
		expect(
			await screen.findByText(
				"No albums in this circle yet. Create the first one below.",
			),
		).toBeInTheDocument();
		fireEvent.change(screen.getByLabelText("New album name"), {
			target: { value: "Grandma's visit" },
		});
		await act(async () =>
			fireEvent.click(screen.getByRole("button", { name: "Create" })),
		);

		expect(create).toHaveBeenCalledWith({
			circle: 7,
			name: "Grandma's visit",
			keep: keep.id,
		});
		expect(
			await screen.findByRole("checkbox", { name: /Grandma's visit/ }),
		).toBeChecked();
		expect(screen.getByLabelText("New album name")).toHaveValue("");
	});

	it("closes with Done", async () => {
		vi.spyOn(albumServices, "list").mockResolvedValue(albumPage([]));

		const { onOpenChange } = renderDialog();
		fireEvent.click(await screen.findByRole("button", { name: "Done" }));

		expect(onOpenChange).toHaveBeenCalledWith(false);
	});

	it("opens from a post's action row", async () => {
		const list = vi
			.spyOn(albumServices, "list")
			.mockResolvedValue(albumPage([beach]));

		renderWithQueryClient(<KeepFeedPost keep={keep} />);
		// Nothing is fetched until the dialog opens.
		expect(list).not.toHaveBeenCalled();
		fireEvent.click(screen.getByRole("button", { name: "Add to album" }));

		expect(
			await screen.findByRole("dialog", { name: "Add to album" }),
		).toBeInTheDocument();
		expect(
			await screen.findByRole("checkbox", { name: /Beach trip/ }),
		).toBeChecked();
	});
});
