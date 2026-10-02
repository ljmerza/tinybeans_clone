import "@/i18n/config";
import { circleServices } from "@/features/circles";
import { renderWithQueryClient } from "@/test-utils";
import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { albumServices } from "../api/services";
import { makeAlbum } from "../testData";
import { AlbumFormDialog } from "./AlbumFormDialog";

const membership = (
	id: number,
	name: string,
	role: "admin" | "member" = "admin",
) => ({
	membership_id: id,
	circle: { id, name, slug: name.toLowerCase(), member_count: 2 },
	role,
	is_owner: false,
	created_at: "2026-01-01T00:00:00Z",
});

function mockCircles(...circles: ReturnType<typeof membership>[]) {
	vi.spyOn(circleServices, "listMemberships").mockResolvedValue({
		data: { circles },
	});
}

beforeEach(() => {
	// Radix Select scrolls the chosen option into view, which jsdom lacks.
	Element.prototype.scrollIntoView = vi.fn();
});

afterEach(() => {
	vi.restoreAllMocks();
});

describe("AlbumFormDialog", () => {
	it("creates an album in the only circle without asking which", async () => {
		mockCircles(membership(7, "Family"));
		const created = makeAlbum({ name: "Lake trip" });
		const create = vi.spyOn(albumServices, "create").mockResolvedValue(created);
		const onOpenChange = vi.fn();
		const onSaved = vi.fn();

		renderWithQueryClient(
			<AlbumFormDialog open onOpenChange={onOpenChange} onSaved={onSaved} />,
		);

		expect(
			screen.getByRole("heading", { name: "New album" }),
		).toBeInTheDocument();
		const submit = screen.getByRole("button", { name: "Create album" });
		expect(submit).toBeDisabled();
		fireEvent.change(screen.getByLabelText("Name"), {
			target: { value: "  Lake trip " },
		});
		fireEvent.change(screen.getByLabelText("Description (optional)"), {
			target: { value: "Summer at the lake" },
		});
		await waitFor(() => expect(submit).toBeEnabled());
		expect(screen.queryByRole("combobox")).toBeNull();
		await act(async () => fireEvent.click(submit));

		expect(create).toHaveBeenCalledWith({
			circle: 7,
			name: "Lake trip",
			description: "Summer at the lake",
		});
		await waitFor(() => expect(onSaved).toHaveBeenCalledWith(created));
		expect(onOpenChange).toHaveBeenCalledWith(false);
	});

	it("asks which circle when the viewer is in several", async () => {
		mockCircles(membership(7, "Family"), membership(9, "Cousins"));
		const create = vi
			.spyOn(albumServices, "create")
			.mockResolvedValue(makeAlbum());

		renderWithQueryClient(<AlbumFormDialog open onOpenChange={vi.fn()} />);

		const trigger = await screen.findByRole("combobox", { name: "Circle" });
		await waitFor(() => expect(trigger).toHaveTextContent("Family"));
		// jsdom drops pointer event details, so open it the keyboard way.
		fireEvent.keyDown(trigger, { key: "ArrowDown" });
		fireEvent.click(await screen.findByRole("option", { name: "Cousins" }));
		fireEvent.change(screen.getByLabelText("Name"), {
			target: { value: "Reunion" },
		});
		await act(async () =>
			fireEvent.click(screen.getByRole("button", { name: "Create album" })),
		);

		expect(create).toHaveBeenCalledWith(
			expect.objectContaining({ circle: 9, name: "Reunion" }),
		);
	});

	it("only offers the circles the viewer is an admin of", async () => {
		mockCircles(membership(7, "Family", "member"), membership(9, "Cousins"));
		const create = vi
			.spyOn(albumServices, "create")
			.mockResolvedValue(makeAlbum());

		renderWithQueryClient(<AlbumFormDialog open onOpenChange={vi.fn()} />);

		fireEvent.change(await screen.findByLabelText("Name"), {
			target: { value: "Reunion" },
		});
		// One admin circle: no picker, and the album goes there.
		await waitFor(() =>
			expect(
				screen.queryByRole("combobox", { name: "Circle" }),
			).not.toBeInTheDocument(),
		);
		await act(async () =>
			fireEvent.click(screen.getByRole("button", { name: "Create album" })),
		);

		expect(create).toHaveBeenCalledWith(
			expect.objectContaining({ circle: 9, name: "Reunion" }),
		);
	});

	it("renames an existing album", async () => {
		mockCircles(membership(7, "Family"));
		const album = makeAlbum({ description: "Old" });
		const update = vi
			.spyOn(albumServices, "update")
			.mockResolvedValue({ ...album, name: "Beach week" });
		const onOpenChange = vi.fn();

		renderWithQueryClient(
			<AlbumFormDialog open onOpenChange={onOpenChange} album={album} />,
		);

		expect(
			screen.getByRole("heading", { name: "Edit album" }),
		).toBeInTheDocument();
		const name = screen.getByLabelText("Name");
		expect(name).toHaveValue("Beach trip 2026");
		fireEvent.change(name, { target: { value: "Beach week" } });
		await act(async () =>
			fireEvent.click(screen.getByRole("button", { name: "Save" })),
		);

		expect(update).toHaveBeenCalledWith(album.id, {
			name: "Beach week",
			description: "Old",
		});
		await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false));
	});

	it("stays open when saving fails", async () => {
		mockCircles(membership(7, "Family"));
		vi.spyOn(albumServices, "create").mockRejectedValue(new Error("down"));
		const onOpenChange = vi.fn();

		renderWithQueryClient(<AlbumFormDialog open onOpenChange={onOpenChange} />);

		fireEvent.change(screen.getByLabelText("Name"), {
			target: { value: "Lake trip" },
		});
		const submit = screen.getByRole("button", { name: "Create album" });
		await waitFor(() => expect(submit).toBeEnabled());
		await act(async () => fireEvent.click(submit));

		expect(onOpenChange).not.toHaveBeenCalled();
		expect(screen.getByLabelText("Name")).toHaveValue("Lake trip");
	});
});
