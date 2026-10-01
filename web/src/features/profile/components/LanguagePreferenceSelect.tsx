import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import {
	SUPPORTED_LANGUAGES,
	toSupportedLanguage,
} from "@/i18n/browserLanguage";
import { useTranslation } from "react-i18next";
import { useUpdateUserProfileMutation } from "../hooks/useUpdateUserProfileMutation";

/**
 * Switches the UI language immediately and saves it to the profile.
 * If the save fails, the previous language is restored.
 */
export function LanguagePreferenceSelect() {
	const { t, i18n } = useTranslation();
	const updateProfile = useUpdateUserProfileMutation({
		suppressSuccessToast: true,
	});
	// resolvedLanguage is the language actually on screen: if a locale chunk
	// failed to load, it stays "en" even though i18n.language changed.
	const currentLanguage = toSupportedLanguage(i18n.resolvedLanguage);

	const handleLanguageChange = async (value: string) => {
		const nextLanguage = toSupportedLanguage(value);
		if (nextLanguage === currentLanguage) return;
		const previousLanguage = currentLanguage;

		try {
			await i18n.changeLanguage(nextLanguage);
			// changeLanguage resolves even when the locale chunk fails to load
			// (e.g. offline), so check the strings actually arrived.
			if (!i18n.hasResourceBundle(nextLanguage, "translation")) {
				throw new Error(`Could not load the "${nextLanguage}" translations`);
			}
			await updateProfile.mutateAsync({ language: nextLanguage });
		} catch (error) {
			console.error("Failed to change language:", error);
			await i18n.changeLanguage(previousLanguage);
		}
	};

	return (
		<Select
			value={currentLanguage}
			onValueChange={(value) => void handleLanguageChange(value)}
			disabled={updateProfile.isPending}
		>
			<SelectTrigger
				className="w-52"
				aria-label={t("twofa.settings.general.language.select_label")}
			>
				<SelectValue
					placeholder={t("twofa.settings.general.language.select_placeholder")}
				/>
			</SelectTrigger>
			<SelectContent align="end">
				{SUPPORTED_LANGUAGES.map((code) => (
					<SelectItem key={code} value={code}>
						<span lang={code}>
							{t(`twofa.settings.general.language.options.${code}`)}
						</span>
					</SelectItem>
				))}
			</SelectContent>
		</Select>
	);
}
