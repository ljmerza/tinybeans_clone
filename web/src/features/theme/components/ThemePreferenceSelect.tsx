import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { useTranslation } from "react-i18next";
import type { ThemePreference } from "../ThemeProvider";
import { useTheme } from "../ThemeProvider";

const THEME_OPTIONS = ["light", "dark", "system"] as const;

export function ThemePreferenceSelect() {
	const { preference, setPreference } = useTheme();
	const { t } = useTranslation();

	return (
		<Select
			value={preference}
			onValueChange={(value) => setPreference(value as ThemePreference)}
		>
			<SelectTrigger className="w-52">
				<SelectValue
					placeholder={t("twofa.settings.general.theme.select_placeholder")}
				/>
			</SelectTrigger>
			<SelectContent align="end">
				{THEME_OPTIONS.map((option) => (
					<SelectItem key={option} value={option}>
						<span className="flex flex-col">
							<span className="text-sm font-medium">
								{t(`twofa.settings.general.theme.options.${option}.title`)}
							</span>
							<span className="text-xs text-muted-foreground">
								{t(
									`twofa.settings.general.theme.options.${option}.description`,
								)}
							</span>
						</span>
					</SelectItem>
				))}
			</SelectContent>
		</Select>
	);
}
