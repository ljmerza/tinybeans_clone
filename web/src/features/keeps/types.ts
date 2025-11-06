export type KeepTypeValue = "note" | "media" | "milestone";

export interface KeepSummary {
	id: string;
	circle: number;
	circle_name?: string;
	created_by: number;
	created_by_display_name?: string;
	keep_type: KeepTypeValue;
	title: string;
	description: string;
	date_of_memory: string;
	created_at: string;
	updated_at: string;
	is_public: boolean;
	tags: string;
	tag_list?: string[];
	media_count?: number;
	reaction_count?: number;
	comment_count?: number;
}

export interface MediaUrls {
	original: string;
	gallery?: string;
	thumbnail?: string;
}

export interface KeepMediaFile {
	id: number;
	keep: string;
	media_type: "photo" | "video";
	caption: string;
	upload_order: number;
	file_size: number | null;
	original_filename: string;
	content_type: string;
	width: number | null;
	height: number | null;
	thumbnails_generated: boolean;
	urls?: MediaUrls;
	created_at: string;
}

export interface KeepDetail extends KeepSummary {
	media_files: KeepMediaFile[];
}

export type MediaUploadState =
	| "pending"
	| "validating"
	| "processing"
	| "completed"
	| "failed";

export interface MediaUploadRecord {
	id: string;
	keep: string;
	keep_title?: string;
	media_type: "photo" | "video";
	original_filename: string;
	content_type: string;
	file_size: number;
	caption: string;
	upload_order: number;
	status: MediaUploadState;
	error_message: string;
	created_at: string;
	updated_at: string;
}

export interface MediaUploadStatusRecord extends MediaUploadRecord {
	progress_percentage?: number | null;
	media_urls?: MediaUrls | null;
}

export interface PaginatedResponse<T> {
	count: number;
	next: string | null;
	previous: string | null;
	results: T[];
}
