import { cn } from "@/lib/utils";
import { useId } from "react";
import { useTranslation } from "react-i18next";
import { useOnThisDayFrequency } from "../hooks/useOnThisDayFrequency";
import { ON_THIS_DAY_FREQUENCIES } from "../utils/onThisDay";

export interface OnThisDayFrequencyToggleProps {
	className?: string;
}

/**
 * A segmented switch for how often "On this day" cards show in the home feed:
 * off, less, normal or more. It saves to the account, so the choice sticks on
 * every device.
 */
export function OnThisDayFrequencyToggle({
	className,
}: OnThisDayFrequencyToggleProps) {
	const { t } = useTranslation();
	const name = useId();
	const { frequency, setFrequency, isSaving } = useOnThisDayFrequency();

	return (
		<div
			role="radiogroup"
			aria-label={t("twofa.settings.general.on_this_day.title")}
			className={cn(
				"inline-flex h-8 items-center rounded-md bg-muted p-0.5 text-xs",
				className,
			)}
		>
			{ON_THIS_DAY_FREQUENCIES.map((option) => (
				<label key={option} className="cursor-pointer">
					<input
						type="radio"
						name={name}
						value={option}
						checked={frequency === option}
						disabled={isSaving}
						onChange={() => void setFrequency(option)}
						className="peer sr-only"
					/>
					<span
						className={cn(
							"flex h-7 items-center rounded px-2.5 font-medium text-muted-foreground",
							"peer-checked:bg-background peer-checked:text-foreground peer-checked:shadow-sm",
							"peer-focus-visible:ring-2 peer-focus-visible:ring-ring peer-disabled:opacity-60",
						)}
					>
						{t(`twofa.settings.general.on_this_day.options.${option}`)}
					</span>
				</label>
			))}
		</div>
	);
}
