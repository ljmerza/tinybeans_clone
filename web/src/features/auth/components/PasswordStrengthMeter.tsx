import { useTranslation } from "react-i18next";

import { cn } from "@/lib/utils";

import {
	type PasswordStrength,
	getPasswordStrength,
} from "../utils/passwordStrength";

const levels: Record<PasswordStrength, { bars: number; color: string }> = {
	too_short: { bars: 0, color: "" },
	weak: { bars: 1, color: "bg-destructive" },
	fair: { bars: 2, color: "bg-amber-400" },
	good: { bars: 3, color: "bg-sky-400" },
	strong: { bars: 4, color: "bg-emerald-500" },
};

/**
 * Four-bar strength gauge shown under the signup password once typing starts.
 */
export function PasswordStrengthMeter({ password }: { password: string }) {
	const { t } = useTranslation();

	if (!password) return null;

	const strength = getPasswordStrength(password);
	const { bars, color } = levels[strength];

	return (
		<div className="space-y-1.5" data-testid="password-strength">
			<div aria-hidden className="grid grid-cols-4 gap-1.5">
				{[1, 2, 3, 4].map((bar) => (
					<div
						key={bar}
						className={cn(
							"h-1.5 rounded-full bg-muted transition-colors",
							bar <= bars && color,
						)}
					/>
				))}
			</div>
			<p className="text-xs text-muted-foreground" aria-live="polite">
				{t("auth.signup.strength.label", {
					level: t(`auth.signup.strength.${strength}`),
				})}
				{strength !== "strong" && <> · {t("auth.signup.strength.hint")}</>}
			</p>
		</div>
	);
}
