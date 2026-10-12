import "@/i18n/config";
import { renderWithQueryClient } from "@/test-utils";
import { screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { OnThisDayCard } from "../components/OnThisDayCard";
import type { FeedKeep } from "../types";
import {
	type FeedRow,
	circleSeed,
	injectOnThisDay,
	localDate,
	onThisDaySeed,
	onThisDaySlots,
	toOnThisDayFrequency,
	yearsAgo,
} from "./onThisDay";

const makeKeep = (id: string, date = "2026-07-04T00:00:00Z"): FeedKeep => ({
	id,
	circle: { id: 1, name: "Merza Family", slug: "merza-family" },
	created_by: 7,
	created_by_display_name: "Leo",
	title: `Keep ${id}`,
	description: "",
	date_of_memory: date,
	created_at: date,
	media: [],
	reaction_count: 0,
	comment_count: 0,
	viewer_reaction: null,
	favorited: false,
	can_delete: false,
	recent_comments: [],
});

const posts = (count: number, prefix = "post") =>
	Array.from({ length: count }, (_, index) => makeKeep(`${prefix}-${index}`));

const memories = (count: number) =>
	Array.from({ length: count }, (_, index) =>
		makeKeep(`memory-${index}`, `${2025 - index}-10-02T12:00:00Z`),
	);

/** Row indexes of the memory cards. */
const cardIndexes = (rows: FeedRow[]) =>
	rows.flatMap((row, index) => (row.kind === "on-this-day" ? [index] : []));

afterEach(() => {
	window.sessionStorage.clear();
	vi.restoreAllMocks();
});

describe("onThisDaySlots", () => {
	it("is the same for the same seed", () => {
		expect(onThisDaySlots(42, 6)).toEqual(onThisDaySlots(42, 6));
	});

	it("varies with the seed", () => {
		const layouts = new Set(
			[1, 2, 3, 4, 5, 6, 7, 8].map((seed) => onThisDaySlots(seed, 4).join(",")),
		);
		expect(layouts.size).toBeGreaterThan(1);
	});

	it("keeps cards off the very top and spreads them out", () => {
		for (let seed = 1; seed <= 200; seed++) {
			const slots = onThisDaySlots(seed, 5);
			expect(slots[0]).toBeGreaterThanOrEqual(3);
			expect(slots[0]).toBeLessThanOrEqual(8);
			for (let index = 1; index < slots.length; index++) {
				const gap = slots[index] - slots[index - 1];
				expect(gap).toBeGreaterThanOrEqual(4);
				expect(gap).toBeLessThanOrEqual(10);
			}
		}
	});

	it("doesn't move earlier slots when there are more cards", () => {
		expect(onThisDaySlots(7, 6).slice(0, 3)).toEqual(onThisDaySlots(7, 3));
	});

	it.each([
		["less", 8, 15, 12, 20],
		["normal", 3, 8, 4, 10],
		["more", 2, 4, 2, 5],
	] as const)(
		"spaces %s cards by that preset's ranges",
		(frequency, firstMin, firstMax, gapMin, gapMax) => {
			for (let seed = 1; seed <= 200; seed++) {
				const slots = onThisDaySlots(seed, 5, frequency);
				expect(slots[0]).toBeGreaterThanOrEqual(firstMin);
				expect(slots[0]).toBeLessThanOrEqual(firstMax);
				for (let index = 1; index < slots.length; index++) {
					const gap = slots[index] - slots[index - 1];
					expect(gap).toBeGreaterThanOrEqual(gapMin);
					expect(gap).toBeLessThanOrEqual(gapMax);
				}
			}
		},
	);

	it("defaults to normal spacing", () => {
		expect(onThisDaySlots(7, 4)).toEqual(onThisDaySlots(7, 4, "normal"));
	});
});

describe("toOnThisDayFrequency", () => {
	it("keeps known values and falls back to normal", () => {
		expect(toOnThisDayFrequency("off")).toBe("off");
		expect(toOnThisDayFrequency("more")).toBe("more");
		expect(toOnThisDayFrequency(undefined)).toBe("normal");
		expect(toOnThisDayFrequency("always")).toBe("normal");
	});
});

describe("injectOnThisDay", () => {
	it("leaves out circles the viewer turned off", () => {
		const rows = injectOnThisDay(posts(20), memories(3), {
			seed: 1,
			complete: true,
			frequencies: { "1": "off" },
		});
		expect(cardIndexes(rows)).toEqual([]);
		expect(rows).toHaveLength(20);
	});

	it("spaces each circle's cards by that circle's frequency", () => {
		const feed = posts(120);
		const family = memories(2);
		const cousins = [0, 1, 2].map((index) => ({
			...makeKeep(`cousins-${index}`, `${2024 - index}-10-02T12:00:00Z`),
			circle: { id: 2, name: "Cousins", slug: "cousins" },
		}));
		const rows = injectOnThisDay(feed, [...family, ...cousins], {
			seed: 4,
			complete: false,
			frequencies: { "1": "less", "2": "more" },
		});

		const expected = [
			...onThisDaySlots(circleSeed(4, 1), 2, "less"),
			...onThisDaySlots(circleSeed(4, 2), 3, "more"),
		].sort((a, b) => a - b);
		// Each card sits after `slot` posts, plus the cards before it.
		expect(cardIndexes(rows)).toEqual(
			expected.map((slot, index) => slot + index),
		);
	});

	it("spaces a circle missing from the frequencies as normal", () => {
		const rows = injectOnThisDay(posts(80), memories(3), {
			seed: 6,
			complete: false,
			frequencies: { "9": "off" },
		});
		expect(cardIndexes(rows)).toEqual(
			onThisDaySlots(circleSeed(6, 1), 3).map((slot, index) => slot + index),
		);
	});

	it("gives each circle its own slots", () => {
		const layouts = new Set(
			[1, 2, 3, 4].map((circleId) =>
				onThisDaySlots(circleSeed(1, circleId), 4).join(","),
			),
		);
		expect(layouts.size).toBeGreaterThan(1);
	});

	it("leaves the feed unchanged with no memories", () => {
		const feed = posts(12);
		const rows = injectOnThisDay(feed, [], { seed: 1, complete: true });

		expect(rows).toEqual(feed.map((keep) => ({ kind: "post", keep })));
	});

	it("puts the cards at the seeded slots, in order", () => {
		const feed = posts(80);
		const memory = memories(3);
		const slots = onThisDaySlots(circleSeed(9, 1), 3);

		const rows = injectOnThisDay(feed, memory, { seed: 9, complete: false });

		// Each card sits after `slot` posts, plus the cards before it.
		expect(cardIndexes(rows)).toEqual(slots.map((slot, index) => slot + index));
		expect(
			rows.filter((row) => row.kind === "on-this-day").map((row) => row.keep),
		).toEqual(memory);
		expect(rows.filter((row) => row.kind === "post")).toHaveLength(80);
	});

	it("keeps rows already shown in place as more pages load", () => {
		const feed = posts(60);
		const memory = memories(5);
		for (let seed = 1; seed <= 50; seed++) {
			let previous: FeedRow[] = [];
			for (let loaded = 10; loaded <= 60; loaded += 10) {
				const rows = injectOnThisDay(feed.slice(0, loaded), memory, {
					seed,
					complete: false,
				});
				// Earlier pages' rows are a prefix of the new rows.
				expect(rows.slice(0, previous.length)).toEqual(previous);
				previous = rows;
			}
		}
	});

	it("waits for the post after a slot before showing its card", () => {
		const [slot] = onThisDaySlots(circleSeed(5, 1), 1);
		const memory = memories(1);

		const short = injectOnThisDay(posts(slot), memory, {
			seed: 5,
			complete: false,
		});
		const longer = injectOnThisDay(posts(slot + 1), memory, {
			seed: 5,
			complete: false,
		});

		expect(cardIndexes(short)).toEqual([]);
		expect(cardIndexes(longer)).toEqual([slot]);
	});

	it("puts cards past the end of a complete feed at the end", () => {
		const rows = injectOnThisDay(posts(2), memories(2), {
			seed: 3,
			complete: true,
		});

		expect(rows.map((row) => row.keep.id)).toEqual([
			"post-0",
			"post-1",
			"memory-0",
			"memory-1",
		]);
	});

	it("skips a card whose keep is the post right before or after it", () => {
		const [slot] = onThisDaySlots(circleSeed(11, 1), 1);
		const feed = posts(30);
		const memory = [feed[slot - 1]];
		expect(
			cardIndexes(injectOnThisDay(feed, memory, { seed: 11, complete: true })),
		).toEqual([]);

		const after = [feed[slot]];
		expect(
			cardIndexes(injectOnThisDay(feed, after, { seed: 11, complete: true })),
		).toEqual([]);

		// Further away it still shows, as its own card.
		const farther = [feed[slot + 2]];
		expect(
			cardIndexes(injectOnThisDay(feed, farther, { seed: 11, complete: true })),
		).toEqual([slot]);
	});
});

describe("onThisDaySeed", () => {
	it("stays the same for the session", () => {
		const random = vi.spyOn(Math, "random");
		const seed = onThisDaySeed();

		expect(seed).toBeGreaterThan(0);
		expect(onThisDaySeed()).toBe(seed);
		expect(random).toHaveBeenCalledTimes(1);
	});
});

describe("dates", () => {
	it("formats the viewer's local day", () => {
		expect(localDate(new Date(2026, 0, 5, 23, 30))).toBe("2026-01-05");
	});

	it("counts years from the memory's UTC date", () => {
		expect(yearsAgo(makeKeep("a", "2023-10-02T23:30:00Z"), "2026-10-02")).toBe(
			3,
		);
		expect(yearsAgo(makeKeep("b", "2024-02-29T12:00:00Z"), "2027-02-28")).toBe(
			3,
		);
	});
});

describe("OnThisDayCard", () => {
	it("labels the post with how long ago it was", () => {
		renderWithQueryClient(
			<OnThisDayCard
				keep={makeKeep("c", "2023-10-02T12:00:00Z")}
				yearsAgo={3}
			/>,
		);

		const card = screen.getByRole("region", {
			name: /on this day.*3 years ago/i,
		});
		expect(card).toContainElement(screen.getByRole("article"));
	});

	it("uses the singular for one year", () => {
		renderWithQueryClient(
			<OnThisDayCard
				keep={makeKeep("d", "2025-10-02T12:00:00Z")}
				yearsAgo={1}
			/>,
		);

		expect(screen.getByText(/1 year ago/)).toBeInTheDocument();
	});
});
