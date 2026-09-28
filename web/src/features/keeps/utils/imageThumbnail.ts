/** Shorter edge of a preview thumbnail: 2x the composer's 80px tiles. */
const THUMBNAIL_EDGE = 160;

// One photo at a time: each full-size decode is tens of MB while it lasts.
let queue: Promise<unknown> = Promise.resolve();

function canvasToJpeg(canvas: HTMLCanvasElement) {
	return new Promise<Blob | null>((resolve) =>
		canvas.toBlob(resolve, "image/jpeg", 0.8),
	);
}

async function shrink(file: Blob): Promise<Blob | null> {
	if (typeof createImageBitmap !== "function") return null;
	// createImageBitmap decodes off the main thread; drawing the result small
	// is cheap. Orientation follows EXIF, like an <img> does.
	const bitmap = await createImageBitmap(file, {
		imageOrientation: "from-image",
	});
	try {
		const scale = Math.min(
			1,
			THUMBNAIL_EDGE / Math.min(bitmap.width, bitmap.height),
		);
		const canvas = document.createElement("canvas");
		canvas.width = Math.max(1, Math.round(bitmap.width * scale));
		canvas.height = Math.max(1, Math.round(bitmap.height * scale));
		const context = canvas.getContext("2d");
		if (!context) return null;
		context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
		return await canvasToJpeg(canvas);
	} finally {
		bitmap.close();
	}
}

/**
 * A small JPEG copy of a photo for previews, so a 12 MP original isn't
 * decoded and rescaled on every paint. Null when the browser can't make one;
 * callers then show the original.
 */
export function makeThumbnail(file: Blob): Promise<Blob | null> {
	const result = queue.then(() => shrink(file)).catch(() => null);
	queue = result;
	return result;
}
