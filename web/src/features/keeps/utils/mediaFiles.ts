/**
 * Which files the composer accepts. No imports, so any module can use these
 * at load time.
 */

/**
 * The server's default limits (MAX_UPLOAD_SIZE / MAX_VIDEO_UPLOAD_SIZE). The
 * live values come from `/keeps/upload/limits/` (see `useUploadLimits`); these
 * apply until it answers.
 */
export const MAX_PHOTO_BYTES = 100 * 1024 * 1024;
export const MAX_VIDEO_BYTES = 1024 * 1024 * 1024;

/** Largest accepted photo and video, in bytes. */
export interface UploadLimits {
	max_photo_bytes: number;
	max_video_bytes: number;
}

export const DEFAULT_UPLOAD_LIMITS: UploadLimits = {
	max_photo_bytes: MAX_PHOTO_BYTES,
	max_video_bytes: MAX_VIDEO_BYTES,
};
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

/** The size limit for a photo or video. */
export function sizeLimitFor(
	mediaType: "photo" | "video",
	limits: UploadLimits = DEFAULT_UPLOAD_LIMITS,
) {
	return mediaType === "video"
		? limits.max_video_bytes
		: limits.max_photo_bytes;
}

/** Why a file can't be posted, or null when it can. */
export function fileProblem(
	file: File,
	limits: UploadLimits = DEFAULT_UPLOAD_LIMITS,
): "type" | "size" | null {
	const mediaType = mediaTypeOf(file);
	if (!mediaType) return "type";
	return file.size > sizeLimitFor(mediaType, limits) ? "size" : null;
}
