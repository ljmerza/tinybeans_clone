/** One height and/or weight reading; stored metric. */
export interface GrowthMeasurement {
	id: string;
	/** `YYYY-MM-DD` */
	measured_on: string;
	height_cm: number | null;
	weight_kg: number | null;
	note: string;
	created_at: string;
	updated_at: string;
}

/** GET /keeps/people/<id>/growth/: a child's log, oldest first. */
export interface GrowthLog {
	/** Whether the viewer may add, change or delete measurements (circle admins). */
	can_edit: boolean;
	/** `YYYY-MM-DD`, when the child's profile has one. */
	birthdate: string | null;
	measurements: GrowthMeasurement[];
}

export interface GrowthMeasurementInput {
	measured_on: string;
	height_cm: number | null;
	weight_kg: number | null;
	note: string;
}

/** A post picked out on the person page. */
export interface PersonStatsPost {
	id: string;
	title: string;
	date_of_memory: string;
	/** Reactions; only set on the most-liked post. */
	like_count: number | null;
	thumbnail_url: string | null;
}

/** GET /keeps/people/<id>/stats/ */
export interface PersonStats {
	birthdate: string | null;
	age: { years: number; months: number; days: number } | null;
	post_count: number;
	photo_count: number;
	video_count: number;
	/** The last 12 UTC months, oldest first; `month` is `YYYY-MM`. */
	posts_per_month: { month: string; count: number }[];
	first_post: PersonStatsPost | null;
	most_liked_post: PersonStatsPost | null;
}
