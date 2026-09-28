import "@/i18n/config";
import { circleServices } from "@/features/circles";
import { renderWithQueryClient } from "@/test-utils";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api/uploadMedia", () => ({ uploadMedia: vi.fn() }));

import { keepServices } from "../api/services";
import { uploadMedia } from "../api/uploadMedia";
import type { FeedKeep } from "../types";
import { NewPostDialog } from "./NewPostDialog";

const KEEP_ID = "00000000-0000-0000-0000-000000000001";

const circle = { id: 7, name: "Family", slug: "family", member_count: 3 };

function renderDialog() {
	const onOpenChange = vi.fn();
	renderWithQueryClient(<NewPostDialog open onOpenChange={onOpenChange} />);
	return { onOpenChange };
}

function pickFiles(files: File[]) {
	fireEvent.change(screen.getByTestId("new-post-files"), {
		target: { files },
	});
}

beforeEach(() => {
	vi.spyOn(circleServices, "listMemberships").mockResolvedValue({
		data: {
			circles: [
				{
					membership_id: 1,
					circle,
					role: "member",
					is_owner: true,
					created_at: "2026-01-01T00:00:00Z",
				},
			],
		},
	});
	vi.spyOn(keepServices, "createKeep").mockImplementation(async (input) => ({
		id: KEEP_ID,
		...input,
	}));
	// Visible in the feed on the first check.
	vi.spyOn(keepServices, "getFeedKeep").mockResolvedValue({} as FeedKeep);
	URL.createObjectURL = vi.fn(() => "blob:preview");
	URL.revokeObjectURL = vi.fn();
});

afterEach(() => {
	vi.restoreAllMocks();
	vi.mocked(uploadMedia).mockReset();
});

describe("NewPostDialog", () => {
	it("posts text on its own as a note", async () => {
		const { onOpenChange } = renderDialog();

		const post = screen.getByRole("button", { name: "Post" });
		expect(post).toBeDisabled();
		fireEvent.change(screen.getByLabelText("What happened?"), {
			target: { value: "  First steps!  " },
		});
		fireEvent.change(screen.getByLabelText("Date"), {
			target: { value: "2026-09-01" },
		});
		await waitFor(() => expect(post).toBeEnabled());
		fireEvent.click(post);

		await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false));
		expect(keepServices.createKeep).toHaveBeenCalledWith(
			expect.objectContaining({
				circle: 7,
				keep_type: "note",
				title: "",
				description: "First steps!",
				date_of_memory: expect.stringMatching(/^2026-09-01T/),
			}),
		);
		expect(uploadMedia).not.toHaveBeenCalled();
	});

	it("creates a media post and uploads each file in order", async () => {
		vi.mocked(uploadMedia).mockImplementation(async (input, onProgress) => {
			onProgress(1);
			return {
				id: `upload-${input.uploadOrder}`,
				keep: input.keepId,
				media_type: input.mediaType,
				original_filename: input.file.name,
				status: "completed",
				error_message: "",
			};
		});
		const { onOpenChange } = renderDialog();
		await screen.findByRole("button", { name: "Post" });

		pickFiles([
			new File(["a"], "beach.jpg", { type: "image/jpeg" }),
			new File(["b"], "waves.png", { type: "image/png" }),
		]);
		expect(screen.getByText("beach.jpg")).toBeInTheDocument();
		await waitFor(() =>
			expect(screen.getByRole("button", { name: "Post" })).toBeEnabled(),
		);
		fireEvent.click(screen.getByRole("button", { name: "Post" }));

		await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false));
		expect(keepServices.createKeep).toHaveBeenCalledWith(
			expect.objectContaining({ keep_type: "media", circle: 7 }),
		);
		const calls = vi
			.mocked(uploadMedia)
			.mock.calls.map(([input]) => [
				input.file.name,
				input.mediaType,
				input.uploadOrder,
				input.keepId,
			]);
		expect(calls).toEqual([
			["beach.jpg", "photo", 0, KEEP_ID],
			["waves.png", "photo", 1, KEEP_ID],
		]);
	});

	it("rejects unsupported and oversized files before uploading", async () => {
		renderDialog();
		await screen.findByRole("button", { name: "Post" });
		const huge = new File(["x"], "huge.jpg", { type: "image/jpeg" });
		Object.defineProperty(huge, "size", { value: 101 * 1024 * 1024 });

		pickFiles([new File(["x"], "notes.txt", { type: "text/plain" }), huge]);

		expect(
			screen.getByText("notes.txt isn't a supported photo or video type."),
		).toBeInTheDocument();
		expect(screen.getByText("huge.jpg is too large.")).toBeInTheDocument();
		expect(screen.queryByRole("list")).not.toBeInTheDocument();
	});

	it("offers retry or discard when an upload fails", async () => {
		vi.mocked(uploadMedia).mockRejectedValue(new Error("network"));
		const deleteKeep = vi
			.spyOn(keepServices, "deleteKeep")
			.mockResolvedValue(undefined);
		const { onOpenChange } = renderDialog();
		await screen.findByRole("button", { name: "Post" });

		pickFiles([new File(["a"], "beach.jpg", { type: "image/jpeg" })]);
		await waitFor(() =>
			expect(screen.getByRole("button", { name: "Post" })).toBeEnabled(),
		);
		fireEvent.click(screen.getByRole("button", { name: "Post" }));

		expect(
			await screen.findByText("Some files didn't upload."),
		).toBeInTheDocument();
		expect(screen.getByText("Upload failed")).toBeInTheDocument();
		expect(
			screen.getByRole("button", { name: "Retry failed uploads" }),
		).toBeInTheDocument();
		// Nothing uploaded, so there's nothing to post without the failures.
		expect(
			screen.queryByRole("button", { name: "Post without them" }),
		).not.toBeInTheDocument();

		fireEvent.click(screen.getByRole("button", { name: "Discard post" }));

		await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false));
		expect(deleteKeep).toHaveBeenCalledWith(KEEP_ID);
	});
});
