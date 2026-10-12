import type { FeedKeep } from "../types";

/** A home feed row: a normal post, or an "On this day" memory card. */
export type FeedRow =
	| { kind: "post"; keep: FeedKeep }
	| { kind: "on-this-day"; keep: FeedKeep };

/** How often the viewer wants memory cards, saved on their account. */
export type OnThisDayFrequency = "off" | "less" | "normal" | "more";

export const DEFAULT_ON_THIS_DAY_FREQUENCY: OnThisDayFrequency = "normal";

export const ON_THIS_DAY_FREQUENCIES: readonly OnThisDayFrequency[] = [
	"off",
	"less",
	"normal",
	"more",
];

export function toOnThisDayFrequency(value: unknown): OnThisDayFrequency {
	return ON_THIS_DAY_FREQUENCIES.includes(value as OnThisDayFrequency)
		? (value as OnThisDayFrequency)
		: DEFAULT_ON_THIS_DAY_FREQUENCY;
}

interface Spacing {
	/** The first card comes after this many posts (inclusive range)... */
	firstMin: number;
	firstMax: number;
	/** ...and each later one this many posts after the previous card. */
	gapMin: number;
	gapMax: number;
}

const SPACING: Record<Exclude<OnThisDayFrequency, "off">, Spacing> = {
	less: { firstMin: 8, firstMax: 15, gapMin: 12, gapMax: 20 },
	normal: { firstMin: 3, firstMax: 8, gapMin: 4, gapMax: 10 },
	more: { firstMin: 2, firstMax: 4, gapMin: 2, gapMax: 5 },
};

/** sessionStorage key holding the per-session seed. */
export const ON_THIS_DAY_SEED_KEY = "keeps:on-this-day-seed";
let fallbackSeed: number | undefined;

/** `YYYY-MM-DD` for a moment in the viewer's own timezone. */
export function localDate(moment: Date) {
	const month = String(moment.getMonth() + 1).padStart(2, "0");
	const day = String(moment.getDate()).padStart(2, "0");
	return `${moment.getFullYear()}-${month}-${day}`;
}

/** Whole years between a memory (stored as a UTC date) and `today` (`YYYY-MM-DD`). */
export function yearsAgo(keep: FeedKeep, today: string) {
	return (
		Number(today.slice(0, 4)) - new Date(keep.date_of_memory).getUTCFullYear()
	);
}

/**
 * A random seed that stays the same for the browser tab's session, so the
 * cards keep their places when the feed remounts or the page reloads.
 */
export function onThisDaySeed(): number {
	try {
		const stored = Number(window.sessionStorage.getItem(ON_THIS_DAY_SEED_KEY));
		if (Number.isInteger(stored) && stored > 0) return stored;
		const seed = randomSeed();
		window.sessionStorage.setItem(ON_THIS_DAY_SEED_KEY, String(seed));
		return seed;
	} catch {
		// Storage can be unavailable (e.g. blocked); keep one per page load.
		fallbackSeed ??= randomSeed();
		return fallbackSeed;
	}
}

function randomSeed() {
	return Math.floor(Math.random() * 0x7fffffff) + 1;
}

/** mulberry32: a small, fast PRNG; the same seed gives the same sequence. */
function seededRandom(seed: number) {
	let state = seed >>> 0;
	return () => {
		state = (state + 0x6d2b79f5) >>> 0;
		let t = state;
		t = Math.imul(t ^ (t >>> 15), t | 1);
		t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
		return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
	};
}

/**
 * How many posts come before each of `count` cards. Depends only on the seed
 * and the count, never on how much of the feed is loaded, so loading more
 * pages can't move a card.
 */
export function onThisDaySlots(
	seed: number,
	count: number,
	frequency: Exclude<OnThisDayFrequency, "off"> = "normal",
): number[] {
	const { firstMin, firstMax, gapMin, gapMax } = SPACING[frequency];
	const random = seededRandom(seed);
	const between = (min: number, max: number) =>
		min + Math.floor(random() * (max - min + 1));
	const slots: number[] = [];
	for (let index = 0; index < count; index++) {
		slots.push(
			index === 0
				? between(firstMin, firstMax)
				: slots[index - 1] + between(gapMin, gapMax),
		);
	}
	return slots;
}

interface InjectOptions {
	seed: number;
	/** Every page of the feed is loaded, so cards past its end go at the end. */
	complete: boolean;
	/** How often cards come up; "off" leaves the posts alone. Default "normal". */
	frequency?: OnThisDayFrequency;
}

/**
 * The feed's posts with "On this day" cards mixed in at seeded random slots.
 *
 * A card shows once the post after its slot is loaded (or the feed is
 * complete), so it is placed in the same render as its neighbours and later
 * pages only ever add rows below it. A card is skipped when the same keep is
 * the post right before or after it, rather than showing it twice in a row.
 * With no memories, or the frequency "off", the posts come back unchanged.
 */
export function injectOnThisDay(
	posts: readonly FeedKeep[],
	memories: readonly FeedKeep[],
	{ seed, complete, frequency = DEFAULT_ON_THIS_DAY_FREQUENCY }: InjectOptions,
): FeedRow[] {
	const rows: FeedRow[] = posts.map((keep) => ({ kind: "post", keep }));
	if (memories.length === 0 || frequency === "off") return rows;

	const slots = onThisDaySlots(seed, memories.length, frequency);
	// Insert from the bottom up so earlier slots still index the posts.
	const placed: Array<{ slot: number; keep: FeedKeep }> = [];
	memories.forEach((keep, index) => {
		let slot = slots[index];
		if (slot >= posts.length) {
			if (!complete) return;
			slot = posts.length;
		}
		const before = posts[slot - 1];
		const after = posts[slot];
		if (before?.id === keep.id || after?.id === keep.id) return;
		placed.push({ slot, keep });
	});

	for (let index = placed.length - 1; index >= 0; index--) {
		const { slot, keep } = placed[index];
		// Cards are placed in slot order, so cards sharing the end slot stay in order.
		rows.splice(slot, 0, { kind: "on-this-day", keep });
	}
	return rows;
}
