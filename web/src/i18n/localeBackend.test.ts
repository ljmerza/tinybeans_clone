import i18next from "i18next";
import { describe, expect, it, vi } from "vitest";
import { createLocaleBackend } from "./localeBackend";

type Loaders = Parameters<typeof createLocaleBackend>[0];

const english = { greeting: "Hello", farewell: "Goodbye" };

async function createI18n(loaders: Loaders, lng = "en") {
	const instance = i18next.createInstance();
	await instance.use(createLocaleBackend(loaders)).init({
		resources: { en: { translation: english } },
		partialBundledLanguages: true,
		lng,
		fallbackLng: "en",
	});
	return instance;
}

describe("createLocaleBackend", () => {
	it("loads a non-English locale only when it's requested", async () => {
		const loadItalian = vi.fn(async () => ({
			default: { greeting: "Ciao" },
		}));
		const i18n = await createI18n({ it: loadItalian });

		expect(loadItalian).not.toHaveBeenCalled();
		expect(i18n.t("greeting")).toBe("Hello");

		const switching = i18n.changeLanguage("it");
		// The language only switches once its strings are in.
		expect(i18n.language).toBe("en");
		await switching;

		expect(loadItalian).toHaveBeenCalledTimes(1);
		expect(i18n.language).toBe("it");
		expect(i18n.t("greeting")).toBe("Ciao");
		// Keys the locale lacks still fall back to English.
		expect(i18n.t("farewell")).toBe("Goodbye");
	});

	it("waits for the startup language's chunk before initializing", async () => {
		const i18n = await createI18n(
			{ es: async () => ({ default: { greeting: "Hola" } }) },
			"es",
		);

		expect(i18n.isInitialized).toBe(true);
		expect(i18n.t("greeting")).toBe("Hola");
	});

	it("keeps English working when a locale chunk fails to load", async () => {
		const loadItalian = vi.fn(() =>
			Promise.reject(new Error("Failed to fetch dynamically imported module")),
		);
		const i18n = await createI18n({ it: loadItalian });

		await expect(i18n.changeLanguage("it")).resolves.toBeTypeOf("function");

		// Not retried: a failed chunk would just fail again.
		expect(loadItalian).toHaveBeenCalledTimes(1);
		expect(i18n.hasResourceBundle("it", "translation")).toBe(false);
		expect(i18n.resolvedLanguage).toBe("en");
		expect(i18n.t("greeting")).toBe("Hello");
	});

	it("still initializes in English when the startup chunk fails", async () => {
		const i18n = await createI18n(
			{ es: () => Promise.reject(new Error("offline")) },
			"es",
		);

		expect(i18n.isInitialized).toBe(true);
		expect(i18n.resolvedLanguage).toBe("en");
		expect(i18n.t("greeting")).toBe("Hello");
	});
});
