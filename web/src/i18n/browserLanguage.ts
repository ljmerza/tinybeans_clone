/**
 * Maps browser language tags onto the UI languages the app ships.
 */
export const SUPPORTED_LANGUAGES = ["en", "es", "it"] as const;

export type SupportedLanguage = (typeof SUPPORTED_LANGUAGES)[number];

export const DEFAULT_LANGUAGE: SupportedLanguage = "en";

type NavigatorLanguages = Pick<Navigator, "language" | "languages">;

function isSupportedLanguage(
	code: string | undefined,
): code is SupportedLanguage {
	return (
		code !== undefined &&
		(SUPPORTED_LANGUAGES as readonly string[]).includes(code)
	);
}

function matchLanguage(
	tag: string | null | undefined,
): SupportedLanguage | null {
	const primary = tag?.trim().toLowerCase().split(/[-_]/)[0];
	return isSupportedLanguage(primary) ? primary : null;
}

/** Maps a single language tag (e.g. "es-MX") to a supported language, defaulting to English. */
export function toSupportedLanguage(
	tag: string | null | undefined,
): SupportedLanguage {
	return matchLanguage(tag) ?? DEFAULT_LANGUAGE;
}

/**
 * Picks the first supported language from the browser's preference list
 * (`navigator.languages`, then `navigator.language`). Regional variants map to
 * their base language ("es-MX" -> "es", "it-CH" -> "it"); anything unsupported
 * falls back to "en".
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
