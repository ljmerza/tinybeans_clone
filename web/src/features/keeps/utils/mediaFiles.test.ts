import { describe, expect, it } from "vitest";

import {
	MAX_PHOTO_BYTES,
	MAX_VIDEO_BYTES,
	fileProblem,
	mediaTypeOf,
} from "./mediaFiles";

function sized(name: string, type: string, size: number) {
	const file = new File(["x"], name, { type });
	Object.defineProperty(file, "size", { value: size });
	return file;
}

describe("fileProblem", () => {
	it("classifies photos and videos by MIME type", () => {
		expect(mediaTypeOf(sized("a.jpg", "image/jpeg", 1))).toBe("photo");
		expect(mediaTypeOf(sized("a.mov", "video/quicktime", 1))).toBe("video");
		expect(mediaTypeOf(sized("a.heic", "image/heic", 1))).toBeNull();
	});

	it("applies the larger limit to videos", () => {
		expect(fileProblem(sized("a.jpg", "image/jpeg", MAX_PHOTO_BYTES))).toBe(
			null,
		);
		expect(fileProblem(sized("a.jpg", "image/jpeg", MAX_PHOTO_BYTES + 1))).toBe(
			"size",
		);
		expect(
			fileProblem(sized("a.mp4", "video/mp4", MAX_PHOTO_BYTES + 1)),
		).toBeNull();
		expect(fileProblem(sized("a.mp4", "video/mp4", MAX_VIDEO_BYTES + 1))).toBe(
			"size",
		);
		expect(fileProblem(sized("a.txt", "text/plain", 1))).toBe("type");
	});
});
