import i18n from "@/i18n/config";
import { describe, expect, it } from "vitest";

import type { FeedMilestone } from "../types";
import { describeMilestone, formatChildAge } from "./milestones";

const t = i18n.t.bind(i18n);

const milestone = (overrides: Partial<FeedMilestone> = {}): FeedMilestone => ({
	milestone_type: "first_steps",
	child: { id: "c1", display_name: "Emma" },
	child_age: { years: 1, months: 2, days: 3 },
	age_at_milestone: "",
	...overrides,
});

describe("formatChildAge", () => {
	it.each([
		[{ years: 1, months: 2, days: 3 }, "1 yr 2 mo"],
		[{ years: 2, months: 0, days: 10 }, "2 yrs"],
		[{ years: 0, months: 5, days: 0 }, "5 mo"],
		[{ years: 0, months: 1, days: 20 }, "1 mo"],
		[{ years: 0, months: 0, days: 15 }, "2 wks"],
		[{ years: 0, months: 0, days: 7 }, "1 wk"],
		[{ years: 0, months: 0, days: 1 }, "1 day"],
		[{ years: 0, months: 0, days: 0 }, "0 days"],
	])("formats %o as %s", (age, expected) => {
		expect(formatChildAge(t, age)).toBe(expected);
	});
});

describe("describeMilestone", () => {
	it("names the milestone, the child and their age", () => {
		expect(describeMilestone(t, milestone())).toBe(
			"First steps · Emma, 1 yr 2 mo",
		);
	});

	it("leaves out what isn't known", () => {
		expect(describeMilestone(t, milestone({ child_age: null }))).toBe(
			"First steps · Emma",
		);
		expect(
			describeMilestone(
				t,
				milestone({ milestone_type: "birthday", child: null, child_age: null }),
			),
		).toBe("Birthday");
	});

	it("falls back to an age typed in by hand", () => {
		expect(
			describeMilestone(
				t,
				milestone({ child_age: null, age_at_milestone: "18 months" }),
			),
		).toBe("First steps · Emma, 18 months");
		expect(
			describeMilestone(
				t,
				milestone({
					milestone_type: "other",
					child: null,
					child_age: null,
					age_at_milestone: "18 months",
				}),
			),
		).toBe("Milestone · 18 months");
	});
});
