import { afterEach, describe, expect, it, vi } from "vitest";
import i18n, { i18nReady } from "./config";
import { localeLoaders } from "./localeBackend";

afterEach(async () => {
	vi.restoreAllMocks();
	await i18n.changeLanguage("en");
});

describe("i18n config", () => {
	it("bundles English only and is ready without loading anything", async () => {
		const loadSpanish = vi.spyOn(localeLoaders, "es");
		const loadItalian = vi.spyOn(localeLoaders, "it");
		await i18nReady;

		expect(i18n.isInitialized).toBe(true);
		expect(i18n.language).toBe("en");
		expect(i18n.t("twofa.settings.general.language.select_label")).toBe(
			"Display language",
		);
		expect(i18n.hasResourceBundle("es", "translation")).toBe(false);
		expect(i18n.hasResourceBundle("it", "translation")).toBe(false);
		expect(loadSpanish).not.toHaveBeenCalled();
		expect(loadItalian).not.toHaveBeenCalled();
	});

	it("loads Italian on demand when the language changes", async () => {
		const loadItalian = vi.spyOn(localeLoaders, "it");

		await i18n.changeLanguage("it");

		expect(loadItalian).toHaveBeenCalledTimes(1);
		expect(i18n.language).toBe("it");
		expect(i18n.resolvedLanguage).toBe("it");
		expect(i18n.t("twofa.settings.general.language.select_label")).toBe(
			"Lingua dell'interfaccia",
		);
		expect(i18n.t("pages.feed.new_post.submit", { count: 3 })).toBe(
			"Pubblica 3",
		);
	});
});
