import "@/i18n/config";
import { circleServices } from "@/features/circles";
import { renderWithQueryClient } from "@/test-utils";
import {
	act,
	fireEvent,
	screen,
	waitFor,
	within,
} from "@testing-library/react";
import { type ReactNode, StrictMode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// The no-circles link; outside a router a plain anchor will do.
vi.mock("@tanstack/react-router", async (importOriginal) => ({
	...(await importOriginal<typeof import("@tanstack/react-router")>()),
	Link: ({ children, to }: { children?: ReactNode; to: string }) => (
		<a href={to}>{children}</a>
	),
}));
vi.mock("../api/uploadMedia", () => ({ uploadMedia: vi.fn() }));
vi.mock("../utils/exifDate", () => ({ readExifDate: vi.fn() }));

import { keepServices } from "../api/services";
import { type UploadMediaInput, uploadMedia } from "../api/uploadMedia";
import type { FeedKeep, MediaUploadRecord } from "../types";
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
	// Visible in the feed on the first check.
	vi.spyOn(keepServices, "getFeedKeep").mockResolvedValue({} as FeedKeep);
	vi.spyOn(keepServices, "getCirclePeople").mockImplementation(
		async (circleId) =>
			circleId === 7
				? [{ id: "p-sophia", name: "Sophia M", kind: "child" }]
				: [{ id: "p-rex", name: "Rex", kind: "pet" }],
	);
	vi.spyOn(keepServices, "getUploadLimits").mockResolvedValue({
		data: {
			max_photo_bytes: 100 * 1024 * 1024,
			max_video_bytes: 1024 * 1024 * 1024,
		},
	});
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
	it("sends someone with no circles to circle setup instead of a picker", async () => {
		vi.mocked(circleServices.listMemberships).mockResolvedValue({
			data: { circles: [] },
		});
		renderDialog();

		const setUp = await screen.findByRole("link", { name: "Set up a circle" });
		expect(setUp).toHaveAttribute("href", "/circles/onboarding");
		expect(screen.queryByTestId("new-post-files")).toBeNull();
		expect(screen.queryByRole("button", { name: "Post" })).toBeNull();
	});

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
		expect(
			screen.getByText("huge.jpg is too large. The limit is 100 MB."),
		).toBeInTheDocument();
		expect(screen.queryByRole("list")).not.toBeInTheDocument();
	});

	it("uses the server's upload limits", async () => {
		vi.mocked(keepServices.getUploadLimits).mockResolvedValue({
			data: {
				max_photo_bytes: 90 * 1024 * 1024,
				max_video_bytes: 90 * 1024 * 1024,
			},
		});
		renderDialog();
		expect(
			await screen.findByText(
				"Photos up to 90 MB (JPEG, PNG, GIF, WebP). Videos up to 90 MB (MP4, MOV, AVI).",
			),
		).toBeInTheDocument();
		const video = new File(["v"], "long.mp4", { type: "video/mp4" });
		Object.defineProperty(video, "size", { value: 91 * 1024 * 1024 });

		pickFiles([video]);

		expect(
			screen.getByText("long.mp4 is too large. The limit is 90 MB."),
		).toBeInTheDocument();
		expect(uploadMedia).not.toHaveBeenCalled();
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

	it("tags the picked people on every post in the batch", async () => {
		vi.mocked(uploadMedia).mockImplementation(async (input) => uploaded(input));
		const { onOpenChange } = renderDialog();
		await screen.findByRole("button", { name: "Post" });

		pickFiles([photo("beach.jpg"), photo("waves.png")]);
		const group = screen.getByRole("group", { name: "Who's in these?" });
		const sophia = await within(group).findByRole("button", {
			name: "Sophia M",
		});
		fireEvent.click(sophia);
		expect(sophia).toHaveAttribute("aria-pressed", "true");
		await clickPost("Post 2");

		await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false));
		expect(
			vi
				.mocked(keepServices.createKeep)
				.mock.calls.map(([input]) => input.people),
		).toEqual([["p-sophia"], ["p-sophia"]]);
		expect(keepServices.getCirclePeople).toHaveBeenCalledWith(7);
	});

	it("drops the picked people when the circle changes", async () => {
		const other = { id: 8, name: "Cousins", slug: "cousins", member_count: 2 };
		vi.mocked(circleServices.listMemberships).mockResolvedValue({
			data: {
				circles: [
					{
						membership_id: 1,
						circle,
						role: "member",
						is_owner: true,
						created_at: "2026-01-01T00:00:00Z",
					},
					{
						membership_id: 2,
						circle: other,
						role: "member",
						is_owner: false,
						created_at: "2026-01-01T00:00:00Z",
					},
				],
			},
		});
		Element.prototype.scrollIntoView = vi.fn();
		vi.mocked(uploadMedia).mockImplementation(async (input) => uploaded(input));
		const { onOpenChange } = renderDialog();
		await screen.findByRole("button", { name: "Post" });
		pickFiles([photo("beach.jpg")]);
		fireEvent.click(await screen.findByRole("button", { name: "Sophia M" }));

		await act(async () =>
			fireEvent.keyDown(screen.getByRole("combobox"), { key: "ArrowDown" }),
		);
		await act(async () =>
			fireEvent.click(await screen.findByRole("option", { name: "Cousins" })),
		);
		const rex = await screen.findByRole("button", { name: "Rex" });
		expect(rex).toHaveAttribute("aria-pressed", "false");
		expect(screen.queryByRole("button", { name: "Sophia M" })).toBeNull();
		await clickPost();

		await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false));
		const [input] = vi.mocked(keepServices.createKeep).mock.calls[0];
		expect(input.circle).toBe(8);
		expect(input.people).toBeUndefined();
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
