import { COLOR_THEMES, type ColorTheme, useTheme } from "@/features/theme";
import { cn } from "@/lib/utils";
import { Check } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useUpdateUserProfileMutation } from "../hooks/useUpdateUserProfileMutation";

/**
 * Swatch grid for the color palette. Applies the choice immediately and saves
 * it to the profile; if the save fails, the previous palette is restored.
 */
export function ColorThemePicker() {
	const { t } = useTranslation();
	const { colorTheme, setColorTheme, resolvedTheme } = useTheme();
	const updateProfile = useUpdateUserProfileMutation({
		suppressSuccessToast: true,
	});

	const handleChange = async (nextColorTheme: ColorTheme) => {
		if (nextColorTheme === colorTheme) return;
		const previousColorTheme = colorTheme;

		setColorTheme(nextColorTheme);
		try {
			await updateProfile.mutateAsync({ color_theme: nextColorTheme });
		} catch (error) {
			console.error("Failed to save color theme:", error);
			setColorTheme(previousColorTheme);
		}
	};

	return (
		<div
			role="radiogroup"
			aria-label={t("twofa.settings.general.color_theme.title")}
			className="grid grid-cols-3 gap-3 sm:grid-cols-4"
		>
			{COLOR_THEMES.map((option) => {
				const selected = option === colorTheme;
				return (
					<label key={option} className="cursor-pointer space-y-1.5">
						<input
							type="radio"
							name="color-theme"
							value={option}
							checked={selected}
							disabled={updateProfile.isPending}
							onChange={() => void handleChange(option)}
							className="peer sr-only"
						/>
						{/* Each swatch carries its own palette (and the current mode)
						    so it previews the theme rather than the active one. */}
						<span
							data-color-theme={option}
							className={cn(
								resolvedTheme === "dark" && "dark",
								"flex h-12 items-center justify-center gap-1.5 rounded-md border border-border bg-background",
								"peer-focus-visible:ring-2 peer-focus-visible:ring-ring",
								"peer-checked:ring-2 peer-checked:ring-primary peer-disabled:opacity-60",
							)}
						>
							<span className="size-5 rounded-full bg-primary" />
							<span className="h-5 w-8 rounded-full bg-accent" />
						</span>
						<span className="flex items-center justify-center gap-1 text-xs font-medium">
							{selected && <Check aria-hidden className="size-3" />}
							{t(`twofa.settings.general.color_theme.options.${option}`)}
						</span>
					</label>
				);
			})}
		</div>
	);
}
