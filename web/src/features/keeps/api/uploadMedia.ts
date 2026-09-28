import { refreshAccessToken } from "@/features/auth/api/authClient";
import { authStore } from "@/features/auth/store/authStore";
import {
	API_BASE,
	type HttpError,
	createHttpError,
	getCsrfToken,
} from "@/lib/httpClient";
import type { ApiMessage, ApiResponseWithMessages } from "@/types";

import type { MediaUploadRecord } from "../types";

export interface UploadMediaInput {
	keepId: string;
	mediaType: "photo" | "video";
	file: File;
	/** A video's poster frame; the feed only shows videos that have one. */
	poster?: Blob;
	uploadOrder: number;
}

function parseBody(text: string): unknown {
	if (!text) return undefined;
	try {
		return JSON.parse(text);
	} catch {
		return text;
	}
}

function send(
	body: FormData,
	onProgress: (fraction: number) => void,
	signal?: AbortSignal,
) {
	return new Promise<{ status: number; data: unknown }>((resolve, reject) => {
		const xhr = new XMLHttpRequest();
		xhr.open("POST", `${API_BASE}/keeps/upload/`);
		xhr.withCredentials = true;
		const token = authStore.state.accessToken;
		if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
		const csrfToken = getCsrfToken();
		if (csrfToken) xhr.setRequestHeader("X-CSRFToken", csrfToken);

		xhr.upload.onprogress = (event) => {
			if (event.lengthComputable) onProgress(event.loaded / event.total);
		};
		xhr.onload = () =>
			resolve({ status: xhr.status, data: parseBody(xhr.responseText) });
		xhr.onerror = () => reject(createHttpError("Network error", 0, undefined));
		xhr.onabort = () => reject(new DOMException("Aborted", "AbortError"));
		signal?.addEventListener("abort", () => xhr.abort(), { once: true });
		xhr.send(body);
	});
}

/**
 * POST one file to /keeps/upload/ with upload progress, which `fetch` can't
 * report. Mirrors the shared client's auth: bearer token, CSRF, and one retry
 * after refreshing an expired token.
 */
export async function uploadMedia(
	{ keepId, mediaType, file, poster, uploadOrder }: UploadMediaInput,
	onProgress: (fraction: number) => void,
	signal?: AbortSignal,
): Promise<MediaUploadRecord> {
	const body = new FormData();
	body.append("keep_id", keepId);
	body.append("media_type", mediaType);
	body.append("upload_order", String(uploadOrder));
	body.append("file", file);
	if (poster) body.append("poster", poster, "poster.jpg");

	let response = await send(body, onProgress, signal);
	if (response.status === 401 && (await refreshAccessToken())) {
		onProgress(0);
		response = await send(body, onProgress, signal);
	}

	const payload = response.data as
		| (ApiResponseWithMessages<MediaUploadRecord> & {
				error?: string;
				messages?: ApiMessage[];
		  })
		| undefined;
	if (response.status < 200 || response.status >= 300 || !payload?.data) {
		const error: HttpError = createHttpError(
			payload?.error ?? "Upload failed",
			response.status,
			payload,
			payload?.messages,
		);
		throw error;
	}
	return payload.data;
}
