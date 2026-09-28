import { describe, expect, it } from "vitest";

import { memoryTimestamp } from "./useCreatePost";

describe("memoryTimestamp", () => {
	it("keeps the chosen day and borrows the current UTC time of day", () => {
		expect(
			memoryTimestamp("2026-09-01", new Date("2026-09-28T23:30:05.123Z")),
		).toBe("2026-09-01T23:30:05.123Z");
	});
});
