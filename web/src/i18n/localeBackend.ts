/**
 * Loads non-English locales on demand.
 *
 * English is bundled with the app: it's the default language and the fallback
 * for every other one. Every other locale is its own lazily loaded chunk, so a
 * user only downloads the language they actually use.
 */
import type { BackendModule, ResourceKey } from "i18next";
import type { SupportedLanguage } from "./browserLanguage";

type LocaleLoader = () => Promise<{ default: ResourceKey }>;

/** Every supported language except the bundled English one. */
export type LazyLanguage = Exclude<SupportedLanguage, "en">;

/**
 * One literal `import()` per locale so Vite emits one hashed chunk per file.
 * Don't replace this with a template-literal import: that would also match
 * `en.json` and split English out of the main bundle.
 *
 * Exported so tests can make a chunk fail.
 */
export const localeLoaders: Record<LazyLanguage, LocaleLoader> = {
	es: () => import("./locales/es.json"),
	it: () => import("./locales/it.json"),
};

/**
 * An i18next backend that reads locales from `loaders`. Pair it with
 * `partialBundledLanguages: true` so the bundled English resources stay put.
 */
export function createLocaleBackend(
	loaders: Partial<Record<string, LocaleLoader>> = localeLoaders,
): BackendModule {
	return {
		type: "backend",
		init() {},
		read(language, _namespace, callback) {
			const load = loaders[language];
			if (!load) {
				callback(new Error(`No locale for "${language}"`), false);
				return;
			}
			load().then(
				(module) => callback(null, module.default),
				// `false` stops i18next retrying: a failed chunk fails the same way
				// again. The UI stays on the English fallback.
				(error: unknown) =>
					callback(error instanceof Error ? error : String(error), false),
			);
		},
	};
}
