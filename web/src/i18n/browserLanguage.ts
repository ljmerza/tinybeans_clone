/**
 * Maps browser language tags onto the UI languages the app ships.
 */
export const SUPPORTED_LANGUAGES = ["en", "es"] as const;

export type SupportedLanguage = (typeof SUPPORTED_LANGUAGES)[number];

export const DEFAULT_LANGUAGE: SupportedLanguage = "en";

type NavigatorLanguages = Pick<Navigator, "language" | "languages">;

function matchLanguage(
	tag: string | null | undefined,
): SupportedLanguage | null {
	const primary = tag?.trim().toLowerCase().split(/[-_]/)[0];
	return primary === "es" ? "es" : primary === "en" ? "en" : null;
}

/** Maps a single language tag (e.g. "es-MX") to a supported language, defaulting to English. */
export function toSupportedLanguage(
	tag: string | null | undefined,
): SupportedLanguage {
	return matchLanguage(tag) ?? DEFAULT_LANGUAGE;
}

/**
 * Picks the first supported language from the browser's preference list
 * (`navigator.languages`, then `navigator.language`). Spanish variants map to
 * "es"; anything unsupported falls back to "en".
 */
export function getBrowserLanguage(
	nav: NavigatorLanguages | undefined = typeof navigator === "undefined"
		? undefined
		: navigator,
): SupportedLanguage {
	const tags = [...(nav?.languages ?? []), nav?.language];
	for (const tag of tags) {
		const match = matchLanguage(tag);
		if (match) return match;
	}
	return DEFAULT_LANGUAGE;
}
