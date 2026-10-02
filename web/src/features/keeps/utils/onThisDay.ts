import type { FeedKeep } from "../types";

/** A home feed row: a normal post, or an "On this day" memory card. */
export type FeedRow =
	| { kind: "post"; keep: FeedKeep }
	| { kind: "on-this-day"; keep: FeedKeep };

/** The first card comes after this many posts (inclusive range)... */
const FIRST_SLOT_MIN = 3;
const FIRST_SLOT_MAX = 8;
/** ...and each later one this many posts after the previous card. */
const GAP_MIN = 4;
const GAP_MAX = 10;

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
export function onThisDaySlots(seed: number, count: number): number[] {
	const random = seededRandom(seed);
	const between = (min: number, max: number) =>
		min + Math.floor(random() * (max - min + 1));
	const slots: number[] = [];
	for (let index = 0; index < count; index++) {
		slots.push(
			index === 0
				? between(FIRST_SLOT_MIN, FIRST_SLOT_MAX)
				: slots[index - 1] + between(GAP_MIN, GAP_MAX),
		);
	}
	return slots;
}

interface InjectOptions {
	seed: number;
	/** Every page of the feed is loaded, so cards past its end go at the end. */
	complete: boolean;
}

/**
 * The feed's posts with "On this day" cards mixed in at seeded random slots.
 *
 * A card shows once the post after its slot is loaded (or the feed is
 * complete), so it is placed in the same render as its neighbours and later
 * pages only ever add rows below it. A card is skipped when the same keep is
 * the post right before or after it, rather than showing it twice in a row.
 * With no memories the posts come back unchanged.
 */
export function injectOnThisDay(
	posts: readonly FeedKeep[],
	memories: readonly FeedKeep[],
	{ seed, complete }: InjectOptions,
): FeedRow[] {
	const rows: FeedRow[] = posts.map((keep) => ({ kind: "post", keep }));
	if (memories.length === 0) return rows;

	const slots = onThisDaySlots(seed, memories.length);
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
