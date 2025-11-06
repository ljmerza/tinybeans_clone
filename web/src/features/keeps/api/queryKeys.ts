export const keepsKeys = {
	all: ["keeps"] as const,
	circle: (circleId: number | string) =>
		["keeps", "circle", String(circleId)] as const,
	circleMedia: (circleId: number | string) =>
		["keeps", "circle", String(circleId), "media"] as const,
	detail: (keepId: string) => ["keeps", "detail", keepId] as const,
	uploadStatus: (uploadId: string) =>
		["keeps", "uploads", uploadId] as const,
};
