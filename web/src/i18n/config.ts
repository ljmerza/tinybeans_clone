/**
 * i18n Configuration
 *
 * Provides internationalization support using react-i18next.
 * Backend sends i18n_key and context, frontend handles translation.
 */
import i18next from "i18next";
import { initReactI18next } from "react-i18next";
import { getBrowserLanguage } from "./browserLanguage";
import en from "./locales/en.json";
import es from "./locales/es.json";

i18next.use(initReactI18next).init({
	resources: {
		en: { translation: en },
		es: { translation: es },
	},
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
});

export default i18next;
