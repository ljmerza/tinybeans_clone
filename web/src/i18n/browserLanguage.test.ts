import { describe, expect, it } from "vitest";
import { getBrowserLanguage, toSupportedLanguage } from "./browserLanguage";

const nav = (languages: string[], language = languages[0] ?? "") => ({
	languages,
	language,
});

describe("toSupportedLanguage", () => {
	it.each([
		["es", "es"],
		["es-MX", "es"],
		["ES_es", "es"],
		["it", "it"],
		["it-IT", "it"],
		["IT_ch", "it"],
		["en-GB", "en"],
		["fr-FR", "en"],
		["", "en"],
		[undefined, "en"],
		[null, "en"],
	])("maps %s to %s", (tag, expected) => {
		expect(toSupportedLanguage(tag)).toBe(expected);
	});
});

describe("getBrowserLanguage", () => {
	it("maps a Spanish browser to es", () => {
		expect(getBrowserLanguage(nav(["es-419", "en"]))).toBe("es");
	});

	it("maps an Italian browser to it", () => {
		expect(getBrowserLanguage(nav(["it-IT", "en"]))).toBe("it");
		expect(getBrowserLanguage(nav(["fr-CH", "it-CH", "es"]))).toBe("it");
		expect(getBrowserLanguage(nav([], "it-SM"))).toBe("it");
	});

	it("maps an English browser to en", () => {
		expect(getBrowserLanguage(nav(["en-US", "es"]))).toBe("en");
	});

	it("uses the first supported language in preference order", () => {
		expect(getBrowserLanguage(nav(["fr-FR", "es-ES"]))).toBe("es");
	});

	it("falls back to navigator.language when languages is empty", () => {
		expect(getBrowserLanguage(nav([], "es-AR"))).toBe("es");
	});

	it("defaults to en for unsupported or missing languages", () => {
		expect(getBrowserLanguage(nav(["fr-FR", "de"]))).toBe("en");
		expect(getBrowserLanguage(nav([], ""))).toBe("en");
		expect(getBrowserLanguage(undefined)).toBe("en");
	});
});
