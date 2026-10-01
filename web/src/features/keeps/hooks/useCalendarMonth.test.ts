import { describe, expect, it } from "vitest";

import { currentMonthKey } from "./useCalendarMonth";

describe("currentMonthKey", () => {
	it("uses the local month even after UTC has rolled into the next one", () => {
		// 8:51pm local on Sep 30; in any zone behind UTC this is already Oct 1 UTC.
		expect(currentMonthKey(new Date(2026, 8, 30, 20, 51))).toBe("2026-09");
	});

	it("zero-pads single-digit months", () => {
		expect(currentMonthKey(new Date(2026, 0, 1, 0, 0))).toBe("2026-01");
	});
});
