import { ThemePreferenceSelect, useTheme } from "@/features/theme";
import { useTranslation } from "react-i18next";

export function ProfileGeneralSettingsCard() {
	const { t } = useTranslation();
	const { preference, resolvedTheme } = useTheme();

	const selectedPreferenceLabel = t(
		`twofa.settings.general.theme.options.${preference}.title`,
	);
	const resolvedLabel = t(
		`twofa.settings.general.theme.options.${resolvedTheme}.title`,
	);

	return (
		<div className="space-y-6">
			<div className="bg-card text-card-foreground border border-border rounded-lg shadow-md p-6 space-y-6">
				<div className="space-y-2">
					<h2 className="text-xl font-semibold">
						{t("twofa.settings.general.title")}
					</h2>
					<p className="text-sm text-muted-foreground">
						{t("twofa.settings.general.description")}
					</p>
				</div>

				<div className="space-y-6">
					<div className="space-y-1">
						<h3 className="text-base font-medium">
							{t("twofa.settings.general.theme.title")}
						</h3>
						<p className="text-sm text-muted-foreground">
							{t("twofa.settings.general.theme.description")}
						</p>
					</div>

					<div className="space-y-4">
						<div className="space-y-1">
							<p className="text-sm font-medium">
								{t("twofa.settings.general.theme.select_label")}
							</p>
							<p className="text-sm text-muted-foreground">
								{t("twofa.settings.general.theme.select_description")}
							</p>
						</div>
						<ThemePreferenceSelect />
						<p className="text-xs text-muted-foreground">
							{preference === "system"
								? t("twofa.settings.general.theme.current_value_system", {
										value: resolvedLabel,
									})
								: t("twofa.settings.general.theme.current_value", {
										value: selectedPreferenceLabel,
									})}
						</p>
					</div>
				</div>
			</div>
		</div>
	);
}
