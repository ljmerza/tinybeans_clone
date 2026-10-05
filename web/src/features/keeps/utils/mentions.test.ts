import { describe, expect, it } from "vitest";

import {
	hasMention,
	insertMention,
	matchMentionable,
	mentionQueryAt,
	splitMentions,
} from "./mentions";

const members = [
	{ id: 1, display_name: "Grandma Jo" },
	{ id: 2, display_name: "Uncle Bob" },
	{ id: 3, display_name: "Gus" },
];

describe("mentionQueryAt", () => {
	it("finds the mention being typed before the caret", () => {
		expect(mentionQueryAt("Hi @gra", 7)).toEqual({ start: 3, text: "gra" });
		expect(mentionQueryAt("@", 1)).toEqual({ start: 0, text: "" });
		expect(mentionQueryAt("@Grandma J", 10)).toEqual({
			start: 0,
			text: "Grandma J",
		});
	});

	it("ignores an @ inside a word, like an email address", () => {
		expect(mentionQueryAt("me@gra", 6)).toBeNull();
	});

	it("ignores text without an @ or with a space right after it", () => {
		expect(mentionQueryAt("hello", 5)).toBeNull();
		expect(mentionQueryAt("@ gra", 5)).toBeNull();
	});

	it("only looks before the caret", () => {
		expect(mentionQueryAt("hi @gra", 2)).toBeNull();
	});
});

describe("matchMentionable", () => {
	it("matches the start of the name or any word in it, ignoring case", () => {
		expect(matchMentionable(members, "g").map((m) => m.id)).toEqual([1, 3]);
		expect(matchMentionable(members, "bo").map((m) => m.id)).toEqual([2]);
		expect(matchMentionable(members, "").map((m) => m.id)).toEqual([1, 2, 3]);
		expect(matchMentionable(members, "zz")).toEqual([]);
	});
});

describe("insertMention", () => {
	it("replaces the typed text with the name and a space", () => {
		expect(
			insertMention("Look @gra", { start: 5, text: "gra" }, "Grandma Jo"),
		).toEqual({ text: "Look @Grandma Jo ", caret: 17 });
	});

	it("keeps what follows the caret without doubling the space", () => {
		expect(insertMention("@gr nice", { start: 0, text: "gr" }, "Gus")).toEqual({
			text: "@Gus nice",
			caret: 5,
		});
	});
});

describe("hasMention", () => {
	it("needs the whole name after an @", () => {
		expect(hasMention("hi @Grandma Jo!", "Grandma Jo")).toBe(true);
		expect(hasMention("hi Grandma Jo", "Grandma Jo")).toBe(false);
		expect(hasMention("hi @Gussie", "Gus")).toBe(false);
	});
});

describe("splitMentions", () => {
	it("flags each @mention of a known name", () => {
		expect(
			splitMentions("@Gus and @Grandma Jo, not @Nobody", ["Grandma Jo", "Gus"]),
		).toEqual([
			{ text: "@Gus", mention: true },
			{ text: " and ", mention: false },
			{ text: "@Grandma Jo", mention: true },
			{ text: ", not @Nobody", mention: false },
		]);
	});

	it("prefers the longer of two names that start the same", () => {
		expect(splitMentions("@Ann Lee hi", ["Ann", "Ann Lee"])).toEqual([
			{ text: "@Ann Lee", mention: true },
			{ text: " hi", mention: false },
		]);
	});

	it("treats names as text, not patterns", () => {
		expect(splitMentions("@J.R. hi @JxR", ["J.R."])).toEqual([
			{ text: "@J.R.", mention: true },
			{ text: " hi @JxR", mention: false },
		]);
	});

	it("returns the text whole without mentions", () => {
		expect(splitMentions("plain", [])).toEqual([
			{ text: "plain", mention: false },
		]);
	});
});
