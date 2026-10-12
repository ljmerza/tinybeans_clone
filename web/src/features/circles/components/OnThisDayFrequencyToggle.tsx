import {
	ON_THIS_DAY_FREQUENCIES,
	type OnThisDayFrequency,
} from "@/features/keeps/utils/onThisDay";
import { cn } from "@/lib/utils";
import { useId } from "react";
import { useTranslation } from "react-i18next";

export interface OnThisDayFrequencyToggleProps {
	value: OnThisDayFrequency;
	onChange: (next: OnThisDayFrequency) => void;
	disabled?: boolean;
	className?: string;
}

/**
 * A segmented switch for how often a circle's "On this day" cards show in
 * its members' home feeds: off, less, normal or more.
 */
export function OnThisDayFrequencyToggle({
	value,
	onChange,
	disabled = false,
	className,
}: OnThisDayFrequencyToggleProps) {
	const { t } = useTranslation();
	const name = useId();

	return (
		<div
			role="radiogroup"
			aria-label={t("pages.circles.dashboard.on_this_day.title")}
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
						checked={value === option}
						disabled={disabled}
						onChange={() => onChange(option)}
						className="peer sr-only"
					/>
					<span
						className={cn(
							"flex h-7 items-center rounded px-2.5 font-medium text-muted-foreground",
							"peer-checked:bg-background peer-checked:text-foreground peer-checked:shadow-sm",
							"peer-focus-visible:ring-2 peer-focus-visible:ring-ring peer-disabled:opacity-60",
						)}
					>
						{t(`pages.circles.dashboard.on_this_day.options.${option}`)}
					</span>
				</label>
			))}
		</div>
	);
}
