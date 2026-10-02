import "@/i18n/config";
import { circleServices } from "@/features/circles";
import { renderWithQueryClient } from "@/test-utils";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { StrictMode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api/uploadMedia", () => ({ uploadMedia: vi.fn() }));
vi.mock("../utils/exifDate", () => ({ readExifDate: vi.fn() }));

import { keepServices } from "../api/services";
import { type UploadMediaInput, uploadMedia } from "../api/uploadMedia";
import type { FeedKeep, KeepChild, MediaUploadRecord } from "../types";
import { readExifDate } from "../utils/exifDate";
import { NewPostDialog } from "./NewPostDialog";

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

function photo(name: string, lastModified = Date.UTC(2026, 5, 15, 12)) {
	return new File(["a"], name, { type: "image/jpeg", lastModified });
}

function uploaded(input: UploadMediaInput): MediaUploadRecord {
	return {
		id: `upload-${input.keepId}`,
		keep: input.keepId,
		media_type: input.mediaType,
		original_filename: input.file.name,
		status: "completed",
		error_message: "",
	};
}

async function clickPost(name = "Post") {
	const button = await screen.findByRole("button", { name });
	await waitFor(() => expect(button).toBeEnabled());
	fireEvent.click(button);
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
	let created = 0;
	vi.spyOn(keepServices, "createKeep").mockImplementation(async (input) => ({
		id: `keep-${++created}`,
		...input,
	}));
	vi.spyOn(keepServices, "deleteKeep").mockResolvedValue(undefined);
	vi.spyOn(keepServices, "getChildren").mockResolvedValue([]);
	// Visible in the feed on the first check.
	vi.spyOn(keepServices, "getFeedKeep").mockResolvedValue({} as FeedKeep);
	URL.createObjectURL = vi.fn(() => "blob:preview");
	URL.revokeObjectURL = vi.fn();
	vi.mocked(readExifDate).mockResolvedValue(null);
});

afterEach(() => {
	vi.restoreAllMocks();
	vi.mocked(uploadMedia).mockReset();
	vi.mocked(readExifDate).mockReset();
});

describe("NewPostDialog", () => {
	it("needs at least one photo or video", async () => {
		renderDialog();

		expect(await screen.findByRole("button", { name: "Post" })).toBeDisabled();
		expect(screen.queryByRole("textbox")).toBeNull();
	});

	it("posts each file on its own with its own title and date", async () => {
		vi.mocked(uploadMedia).mockImplementation(async (input, onProgress) => {
			onProgress(1);
			return uploaded(input);
		});
		const { onOpenChange } = renderDialog();
		await screen.findByRole("button", { name: "Post" });

		pickFiles([photo("beach.jpg"), photo("waves.png")]);
		// Dates start from each file's last-modified day.
		expect(screen.getByLabelText("Date for beach.jpg")).toHaveValue(
			"2026-06-15",
		);
		fireEvent.change(screen.getByLabelText("Title for beach.jpg"), {
			target: { value: "  First swim  " },
		});
		fireEvent.change(screen.getByLabelText("Date for waves.png"), {
			target: { value: "2026-06-20" },
		});
		await clickPost("Post 2");

		await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false));
		const created = vi
			.mocked(keepServices.createKeep)
			.mock.calls.map(([input]) => [
				input.keep_type,
				input.circle,
				input.title,
				input.description,
				input.date_of_memory.slice(0, 10),
			]);
		expect(created).toEqual([
			["media", 7, "First swim", "", "2026-06-15"],
			["media", 7, "", "", "2026-06-20"],
		]);
		const uploads = vi
			.mocked(uploadMedia)
			.mock.calls.map(([input]) => [input.file.name, input.keepId]);
		expect(uploads).toEqual([
			["beach.jpg", "keep-1"],
			["waves.png", "keep-2"],
		]);
	});

	it("dates photos by when they were taken", async () => {
		vi.mocked(readExifDate).mockResolvedValue("2024-03-05");
		renderDialog();
		await screen.findByRole("button", { name: "Post" });

		pickFiles([photo("beach.jpg")]);

		await waitFor(() =>
			expect(screen.getByLabelText("Date for beach.jpg")).toHaveValue(
				"2024-03-05",
			),
		);
	});

	it("keeps a date picked before the photo's EXIF date is read", async () => {
		let resolveExif: (date: string) => void = () => {};
		vi.mocked(readExifDate).mockReturnValue(
			new Promise((resolve) => {
				resolveExif = resolve;
			}),
		);
		renderDialog();
		await screen.findByRole("button", { name: "Post" });

		pickFiles([photo("beach.jpg")]);
		const date = screen.getByLabelText("Date for beach.jpg");
		fireEvent.change(date, { target: { value: "2026-01-02" } });
		resolveExif("2024-03-05");

		await new Promise((resolve) => setTimeout(resolve, 0));
		expect(date).toHaveValue("2026-01-02");
	});

	it("previews picked photos under StrictMode", async () => {
		let created = 0;
		URL.createObjectURL = vi.fn(() => `blob:preview-${++created}`);
		const revoked = new Set<string>();
		URL.revokeObjectURL = vi.fn((url: string) => {
			revoked.add(url);
		});
		renderWithQueryClient(
			<StrictMode>
				<NewPostDialog open onOpenChange={vi.fn()} />
			</StrictMode>,
		);
		await screen.findByRole("button", { name: "Post" });

		pickFiles([photo("beach.jpg")]);

		const preview = await waitFor(() => {
			const img = document.querySelector<HTMLImageElement>("li img");
			expect(img).not.toBeNull();
			return img as HTMLImageElement;
		});
		// StrictMode's extra mount/unmount must not leave the image on a revoked URL.
		expect(revoked.has(preview.getAttribute("src") ?? "")).toBe(false);
	});

	it("rejects unsupported and oversized files before uploading", async () => {
		renderDialog();
		await screen.findByRole("button", { name: "Post" });
		const huge = photo("huge.jpg");
		Object.defineProperty(huge, "size", { value: 101 * 1024 * 1024 });

		pickFiles([new File(["x"], "notes.txt", { type: "text/plain" }), huge]);

		expect(
			screen.getByText("notes.txt isn't a supported photo or video type."),
		).toBeInTheDocument();
		expect(screen.getByText("huge.jpg is too large.")).toBeInTheDocument();
		expect(screen.queryByRole("list")).not.toBeInTheDocument();
	});

	it("retries a failed upload into the same post", async () => {
		vi.mocked(uploadMedia)
			.mockRejectedValueOnce(new Error("network"))
			.mockImplementation(async (input) => uploaded(input));
		const { onOpenChange } = renderDialog();
		await screen.findByRole("button", { name: "Post" });

		pickFiles([photo("beach.jpg")]);
		await clickPost();
		fireEvent.click(
			await screen.findByRole("button", { name: "Retry failed uploads" }),
		);

		await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false));
		expect(keepServices.createKeep).toHaveBeenCalledTimes(1);
		expect(
			vi.mocked(uploadMedia).mock.calls.map(([input]) => input.keepId),
		).toEqual(["keep-1", "keep-1"]);
	});

	it("skips failed files and keeps the ones that posted", async () => {
		vi.mocked(uploadMedia).mockImplementation(async (input) => {
			if (input.file.name === "waves.png") throw new Error("network");
			return uploaded(input);
		});
		const { onOpenChange } = renderDialog();
		await screen.findByRole("button", { name: "Post" });

		pickFiles([photo("beach.jpg"), photo("waves.png")]);
		await clickPost("Post 2");

		expect(
			await screen.findByText("Some files didn't upload."),
		).toBeInTheDocument();
		expect(screen.getByText("Uploaded")).toBeInTheDocument();
		expect(screen.getByText("Upload failed")).toBeInTheDocument();
		fireEvent.click(screen.getByRole("button", { name: "Skip failed" }));

		await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false));
		// Only the failed file's empty post goes; the posted one stays.
		expect(keepServices.deleteKeep).toHaveBeenCalledTimes(1);
		expect(keepServices.deleteKeep).toHaveBeenCalledWith("keep-2");
	});

	it("discards when nothing uploaded", async () => {
		vi.mocked(uploadMedia).mockRejectedValue(new Error("network"));
		const { onOpenChange } = renderDialog();
		await screen.findByRole("button", { name: "Post" });

		pickFiles([photo("beach.jpg")]);
		await clickPost();
		fireEvent.click(
			await screen.findByRole("button", { name: "Discard post" }),
		);

		await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false));
		expect(keepServices.deleteKeep).toHaveBeenCalledWith("keep-1");
	});
});

describe("NewPostDialog milestones", () => {
	const child = (
		id: string,
		name: string,
		circleId = circle.id,
	): KeepChild => ({
		id,
		display_name: name,
		circle: { id: circleId, name: "Family", slug: "family" },
		milestone_count: 0,
	});

	beforeEach(() => {
		// Radix Select scrolls the chosen option into view; jsdom can't.
		Element.prototype.scrollIntoView = vi.fn();
		vi.mocked(uploadMedia).mockImplementation(async (input) => uploaded(input));
	});

	function choose(label: string, option: string) {
		fireEvent.keyDown(screen.getByLabelText(label), { key: "ArrowDown" });
		fireEvent.click(screen.getByRole("option", { name: option }));
	}

	async function pickAndOpenMilestone(name: string) {
		await screen.findByRole("button", { name: "Post" });
		pickFiles([photo(name)]);
		fireEvent.click(
			screen.getByRole("button", { name: `Mark ${name} as a milestone` }),
		);
	}

	it("posts a photo as a milestone for a child in its circle", async () => {
		vi.mocked(keepServices.getChildren).mockResolvedValue([
			child("emma", "Emma"),
			child("liam", "Liam"),
			child("elsewhere", "Cousin", 99),
		]);
		const { onOpenChange } = renderDialog();
		await pickAndOpenMilestone("steps.jpg");

		// A milestone needs its type before it can post.
		expect(screen.getByRole("button", { name: "Post" })).toBeDisabled();
		choose("Milestone for steps.jpg", "First steps");
		fireEvent.keyDown(screen.getByLabelText("Child for steps.jpg"), {
			key: "ArrowDown",
		});
		expect(
			screen.getAllByRole("option").map((option) => option.textContent),
		).toEqual(["No one in particular", "Emma", "Liam"]);
		fireEvent.click(screen.getByRole("option", { name: "Liam" }));
		await clickPost();

		await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false));
		expect(keepServices.createKeep).toHaveBeenCalledWith(
			expect.objectContaining({
				keep_type: "milestone",
				milestone_data: {
					milestone_type: "first_steps",
					child_profile: "liam",
				},
			}),
		);
	});

	it("picks an only child for the milestone", async () => {
		vi.mocked(keepServices.getChildren).mockResolvedValue([
			child("emma", "Emma"),
		]);
		renderDialog();
		await waitFor(() => expect(keepServices.getChildren).toHaveBeenCalled());
		await pickAndOpenMilestone("tooth.jpg");

		await waitFor(() =>
			expect(screen.getByLabelText("Child for tooth.jpg")).toHaveTextContent(
				"Emma",
			),
		);
		choose("Milestone for tooth.jpg", "First tooth");
		await clickPost();

		await waitFor(() =>
			expect(keepServices.createKeep).toHaveBeenCalledWith(
				expect.objectContaining({
					milestone_data: {
						milestone_type: "first_tooth",
						child_profile: "emma",
					},
				}),
			),
		);
	});

	it("has no child picker when the circle has no children", async () => {
		renderDialog();
		await pickAndOpenMilestone("party.jpg");

		expect(screen.queryByLabelText("Child for party.jpg")).toBeNull();
		choose("Milestone for party.jpg", "Birthday");
		await clickPost();

		await waitFor(() =>
			expect(keepServices.createKeep).toHaveBeenCalledWith(
				expect.objectContaining({
					keep_type: "milestone",
					milestone_data: { milestone_type: "birthday", child_profile: null },
				}),
			),
		);
	});

	it("posts a plain photo once the milestone is removed", async () => {
		renderDialog();
		await pickAndOpenMilestone("beach.jpg");

		fireEvent.click(
			screen.getByRole("button", {
				name: "Remove the milestone from beach.jpg",
			}),
		);
		await clickPost();

		await waitFor(() => expect(keepServices.createKeep).toHaveBeenCalled());
		const [input] = vi.mocked(keepServices.createKeep).mock.calls[0];
		expect(input.keep_type).toBe("media");
		expect(input).not.toHaveProperty("milestone_data");
	});
});
