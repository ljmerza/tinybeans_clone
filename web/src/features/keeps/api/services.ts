import { apiClient as authApi } from "@/features/auth/api/authClient";
import type { ApiResponseWithMessages } from "@/types";
import type {
	KeepDetail,
	KeepSummary,
	MediaUploadRecord,
	MediaUploadStatusRecord,
	PaginatedResponse,
} from "../types";

function buildQuery(params: Record<string, string | number | undefined>) {
	const searchParams = new URLSearchParams();
	Object.entries(params).forEach(([key, value]) => {
		if (value === undefined || value === null) return;
		searchParams.set(key, String(value));
	});
	const queryString = searchParams.toString();
	return queryString ? `?${queryString}` : "";
}

export const keepsServices = {
	async listCircleKeeps(circleId: number | string, keepType?: string) {
		const query = buildQuery({
			circle: circleId,
			keep_type: keepType,
			ordering: "-date_of_memory",
		});
		return authApi.get<PaginatedResponse<KeepSummary> | KeepSummary[]>(
			`/keeps/${query}`,
		);
	},

	async getKeep(keepId: string) {
		return authApi.get<KeepDetail>(`/keeps/${keepId}/`);
	},

	async createKeep(body: {
		circle: number | string;
		keep_type: string;
		title: string;
		description?: string;
		date_of_memory?: string;
		is_public?: boolean;
		tags?: string;
	}) {
		return authApi.post<KeepDetail>(`/keeps/`, body);
	},

	async uploadMedia(payload: {
		keepId: string;
		file: File;
		mediaType?: "photo" | "video";
		caption?: string;
		uploadOrder?: number;
	}) {
		const formData = new FormData();
		formData.append("keep_id", payload.keepId);
		formData.append("media_type", payload.mediaType ?? "photo");
		formData.append("file", payload.file);
		if (payload.caption) {
			formData.append("caption", payload.caption);
		}
		if (typeof payload.uploadOrder === "number") {
			formData.append("upload_order", String(payload.uploadOrder));
		}

		return authApi.request<ApiResponseWithMessages<MediaUploadRecord>>(
			"/keeps/upload/",
			{
				method: "POST",
				body: formData,
			},
		);
	},

	async getUploadStatus(uploadId: string) {
		return authApi.get<ApiResponseWithMessages<MediaUploadStatusRecord>>(
			`/keeps/upload/${uploadId}/status/`,
		);
	},

	async deleteMedia(mediaId: number | string) {
		return authApi.delete(`/keeps/media/${mediaId}/`);
	},
};
