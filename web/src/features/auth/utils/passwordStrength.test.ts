import { describe, expect, it } from "vitest";

import { getPasswordStrength } from "./passwordStrength";

describe("getPasswordStrength", () => {
	it.each([
		["", "too_short"],
		["Ab1!xyz", "too_short"],
		["password", "weak"],
		["passwordpassword", "fair"],
		["Password1", "fair"],
		["Password1!", "good"],
		["correct horse battery", "good"],
		["Fresh-Lantern-42", "strong"],
	])("rates %j as %s", (password, expected) => {
		expect(getPasswordStrength(password)).toBe(expected);
	});
});
