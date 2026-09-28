/** Longest edge of the captured frame; the server derives 1200px renditions. */
const MAX_POSTER_EDGE = 1600;
/** Seek a little in: the very first frame of phone video is often black. */
const POSTER_TIME_SECONDS = 0.5;
const CAPTURE_TIMEOUT_MS = 15000;
/** Used when this browser can't decode the video (e.g. HEVC on desktop Chrome). */
const FALLBACK_SIZE = { width: 1280, height: 720 };

function canvasToJpeg(canvas: HTMLCanvasElement) {
	return new Promise<Blob | null>((resolve) =>
		canvas.toBlob(resolve, "image/jpeg", 0.85),
	);
}

function drawFrame(video: HTMLVideoElement) {
	const scale = Math.min(
		1,
		MAX_POSTER_EDGE / Math.max(video.videoWidth, video.videoHeight),
	);
	const canvas = document.createElement("canvas");
	canvas.width = Math.round(video.videoWidth * scale);
	canvas.height = Math.round(video.videoHeight * scale);
	canvas.getContext("2d")?.drawImage(video, 0, 0, canvas.width, canvas.height);
	return canvasToJpeg(canvas);
}

function grabFrame(file: File) {
	return new Promise<Blob | null>((resolve) => {
		const url = URL.createObjectURL(file);
		const video = document.createElement("video");
		const finish = (blob: Blob | null) => {
			window.clearTimeout(timer);
			video.removeAttribute("src");
			video.load();
			URL.revokeObjectURL(url);
			resolve(blob);
		};
		const timer = window.setTimeout(() => finish(null), CAPTURE_TIMEOUT_MS);

		video.muted = true;
		video.playsInline = true;
		video.preload = "auto";
		video.onloadedmetadata = () => {
			if (!video.videoWidth || !video.videoHeight) return finish(null);
			video.currentTime = Math.min(POSTER_TIME_SECONDS, video.duration / 2);
		};
		video.onseeked = () => {
			drawFrame(video).then(finish, () => finish(null));
		};
		video.onerror = () => finish(null);
		video.src = url;
	});
}

function placeholderFrame() {
	const canvas = document.createElement("canvas");
	canvas.width = FALLBACK_SIZE.width;
	canvas.height = FALLBACK_SIZE.height;
	const context = canvas.getContext("2d");
	if (context) {
		context.fillStyle = "#1f2937";
		context.fillRect(0, 0, canvas.width, canvas.height);
	}
	return canvasToJpeg(canvas);
}

/**
 * A JPEG poster frame for a video, captured in the browser. The feed only
 * shows videos with a poster, so when this browser can't decode the file a
 * plain dark frame stands in (other devices may still play the video).
 */
export async function captureVideoPoster(file: File): Promise<Blob | null> {
	return (await grabFrame(file)) ?? placeholderFrame();
}
