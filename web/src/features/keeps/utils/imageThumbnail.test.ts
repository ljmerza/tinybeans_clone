import { afterEach, describe, expect, it, vi } from "vitest";

import { makeThumbnail } from "./imageThumbnail";

afterEach(() => {
	vi.unstubAllGlobals();
	vi.restoreAllMocks();
});

function stubCanvas() {
	const drawImage = vi.fn();
	const sizes: Array<[number, number]> = [];
	vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockImplementation(
		function (this: HTMLCanvasElement) {
			return { drawImage } as unknown as CanvasRenderingContext2D;
		},
	);
	vi.spyOn(HTMLCanvasElement.prototype, "toBlob").mockImplementation(function (
		this: HTMLCanvasElement,
		callback: BlobCallback,
	) {
		sizes.push([this.width, this.height]);
		callback(new Blob(["thumb"], { type: "image/jpeg" }));
	});
	return { drawImage, sizes };
}

describe("makeThumbnail", () => {
	it("shrinks the shorter edge to 160px and frees the full-size decode", async () => {
		const close = vi.fn();
		const createImageBitmap = vi.fn(async () => ({
			width: 4032,
			height: 3024,
			close,
		}));
		vi.stubGlobal("createImageBitmap", createImageBitmap);
		const { drawImage, sizes } = stubCanvas();
		const photo = new File(["x"], "beach.jpg", { type: "image/jpeg" });

		const thumbnail = await makeThumbnail(photo);

		expect(thumbnail?.type).toBe("image/jpeg");
		expect(sizes).toEqual([[213, 160]]);
		expect(drawImage).toHaveBeenCalledTimes(1);
		expect(close).toHaveBeenCalled();
		expect(createImageBitmap).toHaveBeenCalledWith(photo, {
			imageOrientation: "from-image",
		});
	});

	it("never enlarges a small image", async () => {
		vi.stubGlobal(
			"createImageBitmap",
			vi.fn(async () => ({ width: 100, height: 50, close: vi.fn() })),
		);
		const { sizes } = stubCanvas();

		await makeThumbnail(new Blob(["x"]));

		expect(sizes).toEqual([[100, 50]]);
	});

	it("returns null when the browser can't decode it", async () => {
		vi.stubGlobal(
			"createImageBitmap",
			vi.fn(async () => {
				throw new Error("unsupported");
			}),
		);

		expect(await makeThumbnail(new Blob(["x"]))).toBeNull();
		// A failure doesn't jam the queue for the next photo.
		vi.stubGlobal(
			"createImageBitmap",
			vi.fn(async () => ({ width: 320, height: 320, close: vi.fn() })),
		);
		stubCanvas();
		expect(await makeThumbnail(new Blob(["x"]))).not.toBeNull();
	});
});
