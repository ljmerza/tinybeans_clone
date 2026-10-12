import { ON_THIS_DAY_FREQUENCIES } from "@/features/keeps/utils/onThisDay";
import { cn } from "@/lib/utils";
import { useId } from "react";
import { useTranslation } from "react-i18next";

import { useCircleOnThisDayFrequency } from "../hooks/useCircleOnThisDayFrequency";

export interface OnThisDayFrequencyToggleProps {
	circleId: number | string;
	className?: string;
}

/**
 * A segmented switch for how often one circle's "On this day" cards show in
 * the viewer's home feed: off, less, normal or more. Each member picks their
 * own for each circle.
 */
export function OnThisDayFrequencyToggle({
	circleId,
	className,
}: OnThisDayFrequencyToggleProps) {
	const { t } = useTranslation();
	const name = useId();
	const { frequency, setFrequency, isSaving } =
		useCircleOnThisDayFrequency(circleId);

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
						checked={frequency === option}
						disabled={isSaving}
						onChange={() => setFrequency(option)}
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
