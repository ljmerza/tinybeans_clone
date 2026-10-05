import type { CommentMention } from "../types";

/** Suggestions shown at once while typing an @mention. */
export const MAX_MENTION_SUGGESTIONS = 6;

/** Longest text after "@" still treated as a name being typed. */
const MAX_QUERY_LENGTH = 50;

/** The @mention being typed: where its "@" is and the text typed after it. */
export interface MentionQuery {
	start: number;
	text: string;
}

const escapeRegExp = (value: string) =>
	value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

// A name only counts when it isn't the start of a longer word ("@Ann" in "@Anna").
const NAME_END = "(?![\\p{L}\\p{N}_])";

/**
 * The @mention being typed just before `caret`, if any. The "@" must start the
 * text or follow whitespace, so email addresses don't open suggestions. Names
 * may contain spaces ("@Grandma Jo").
 */
export function mentionQueryAt(
	text: string,
	caret: number,
): MentionQuery | null {
	const start = text.lastIndexOf("@", caret - 1);
	if (start < 0 || (start > 0 && !/\s/.test(text[start - 1] ?? ""))) {
		return null;
	}
	const typed = text.slice(start + 1, caret);
	if (typed.length > MAX_QUERY_LENGTH || /^\s|\n/.test(typed)) return null;
	return { start, text: typed };
}

/** Members whose name, or any word of it, starts with `query`, ignoring case. */
export function matchMentionable(
	members: CommentMention[],
	query: string,
): CommentMention[] {
	const needle = query.toLocaleLowerCase();
	return members
		.filter((member) => {
			const name = member.display_name.toLocaleLowerCase();
			return (
				name.startsWith(needle) ||
				name.split(/\s+/).some((word) => word.startsWith(needle))
			);
		})
		.slice(0, MAX_MENTION_SUGGESTIONS);
}

/**
 * Replace the mention being typed (from its "@" to `end`) with `@name `.
 * Returns the new text and where the caret goes.
 */
export function insertMention(
	text: string,
	query: MentionQuery,
	name: string,
): { text: string; caret: number } {
	const end = query.start + 1 + query.text.length;
	const inserted = `@${name} `;
	// Don't double the space if one already follows.
	const rest = text.slice(end).replace(/^ /, "");
	return {
		text: text.slice(0, query.start) + inserted + rest,
		caret: query.start + inserted.length,
	};
}

/** Whether `text` still contains `@name`, e.g. after the draft was edited. */
export function hasMention(text: string, name: string): boolean {
	return new RegExp(`@${escapeRegExp(name)}${NAME_END}`, "u").test(text);
}

/** A run of comment text, flagged when it is an @mention. */
export interface MentionSegment {
	text: string;
	mention: boolean;
}

/**
 * Split `text` into plain runs and the @mentions of `names`, so mentions can
 * be highlighted. Longer names win when one name starts another.
 */
export function splitMentions(text: string, names: string[]): MentionSegment[] {
	const unique = [...new Set(names.filter(Boolean))].sort(
		(a, b) => b.length - a.length,
	);
	if (unique.length === 0) return [{ text, mention: false }];
	const pattern = new RegExp(
		`@(?:${unique.map(escapeRegExp).join("|")})${NAME_END}`,
		"gu",
	);
	const segments: MentionSegment[] = [];
	let last = 0;
	for (const match of text.matchAll(pattern)) {
		const index = match.index ?? 0;
		if (index > last) {
			segments.push({ text: text.slice(last, index), mention: false });
		}
		segments.push({ text: match[0], mention: true });
		last = index + match[0].length;
	}
	if (last < text.length) {
		segments.push({ text: text.slice(last), mention: false });
	}
	return segments;
}
