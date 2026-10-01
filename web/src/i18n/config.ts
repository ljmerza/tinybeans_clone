/**
 * i18n Configuration
 *
 * Provides internationalization support using react-i18next.
 * Backend sends i18n_key and context, frontend handles translation.
 */
import i18next from "i18next";
import { initReactI18next } from "react-i18next";
import { getBrowserLanguage } from "./browserLanguage";
import { createLocaleBackend } from "./localeBackend";
import en from "./locales/en.json";

// Keep <html lang> on the language actually shown. resolvedLanguage stays
// "en" when a locale chunk fails and the UI falls back to English.
// Registered before init so the startup language is applied too.
i18next.on("languageChanged", (lng) => {
	document.documentElement.lang = i18next.resolvedLanguage ?? lng;
});

/**
 * Resolves once the startup language can be rendered: straight away for
 * English (bundled), or after its chunk loads for any other language. It also
 * resolves if that chunk fails, leaving the UI on the English fallback.
 * `main.tsx` waits on it before the first render.
 */
export const i18nReady: Promise<void> = i18next
	.use(initReactI18next)
	.use(createLocaleBackend())
	.init({
		// Only English is bundled. Other locales load through the backend when
		// first used; partialBundledLanguages lets the two coexist.
		resources: {
			en: { translation: en },
		},
		partialBundledLanguages: true,
		// Logged-out pages follow the browser; a signed-in user's saved
		// preference is applied by AuthSessionProvider once the session loads.
		lng: getBrowserLanguage(),
		fallbackLng: "en", // missing keys fall back to English
		interpolation: {
			escapeValue: false, // React already escapes
		},
		// Return key if translation is missing (easier debugging)
		returnNull: false,
		returnEmptyString: false,
	})
	.then(
		() => undefined,
		(error: unknown) => {
			console.error("[i18n] Failed to initialize", error);
		},
	);

export default i18next;
