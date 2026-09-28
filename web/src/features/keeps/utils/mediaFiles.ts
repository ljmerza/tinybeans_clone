/**
 * Which files the composer accepts. No imports, so any module can use these
 * at load time.
 */

/** Mirror the server's limits (MAX_UPLOAD_SIZE / MAX_VIDEO_UPLOAD_SIZE). */
export const MAX_PHOTO_BYTES = 100 * 1024 * 1024;
export const MAX_VIDEO_BYTES = 1024 * 1024 * 1024;
/** Mirror ALLOWED_IMAGE_TYPES / ALLOWED_VIDEO_TYPES. */
export const PHOTO_TYPES = [
	"image/jpeg",
	"image/png",
	"image/gif",
	"image/webp",
];
export const VIDEO_TYPES = ["video/mp4", "video/quicktime", "video/x-msvideo"];

export function mediaTypeOf(file: File): "photo" | "video" | null {
	if (PHOTO_TYPES.includes(file.type)) return "photo";
	if (VIDEO_TYPES.includes(file.type)) return "video";
	return null;
}

/** Why a file can't be posted, or null when it can. */
export function fileProblem(file: File): "type" | "size" | null {
	const mediaType = mediaTypeOf(file);
	if (!mediaType) return "type";
	const limit = mediaType === "video" ? MAX_VIDEO_BYTES : MAX_PHOTO_BYTES;
	return file.size > limit ? "size" : null;
}
