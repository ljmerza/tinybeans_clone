import { describe, expect, it } from "vitest";

import { safeRedirectPath } from "./safeRedirect";

describe("safeRedirectPath", () => {
	it("keeps paths on this site", () => {
		expect(safeRedirectPath("/calendar?day=2026-10-01#top")).toBe(
			"/calendar?day=2026-10-01#top",
		);
		expect(safeRedirectPath(`${window.location.origin}/albums`)).toBe(
			"/albums",
		);
	});

	it("refuses anything that leaves the site", () => {
		expect(safeRedirectPath("https://evil.example/login")).toBeNull();
		expect(safeRedirectPath("//evil.example/login")).toBeNull();
		expect(safeRedirectPath("javascript:alert(1)")).toBeNull();
	});

	it("ignores an empty target", () => {
		expect(safeRedirectPath(null)).toBeNull();
		expect(safeRedirectPath("")).toBeNull();
	});
});
