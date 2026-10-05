import { cn } from "@/lib/utils";
import { useId } from "react";
import { useTranslation } from "react-i18next";
import { useMeasurementUnits } from "../hooks/useMeasurementUnits";
import type { MeasurementUnits } from "../utils/units";

const OPTIONS: MeasurementUnits[] = ["imperial", "metric"];

export interface MeasurementUnitsToggleProps {
	className?: string;
}

/**
 * A small two-way switch between lb/in and kg/cm. It saves to the account, so
 * the choice sticks on every device and on the profile settings page.
 */
export function MeasurementUnitsToggle({
	className,
}: MeasurementUnitsToggleProps) {
	const { t } = useTranslation();
	const name = useId();
	const { units, setUnits, isSaving } = useMeasurementUnits();

	return (
		<div
			role="radiogroup"
			aria-label={t("pages.people.growth.units.label")}
			className={cn(
				"inline-flex h-8 items-center rounded-md bg-muted p-0.5 text-xs",
				className,
			)}
		>
			{OPTIONS.map((option) => (
				<label key={option} className="cursor-pointer">
					<input
						type="radio"
						name={name}
						value={option}
						checked={units === option}
						disabled={isSaving}
						onChange={() => void setUnits(option)}
						className="peer sr-only"
					/>
					<span
						className={cn(
							"flex h-7 items-center rounded px-2.5 font-medium text-muted-foreground",
							"peer-checked:bg-background peer-checked:text-foreground peer-checked:shadow-sm",
							"peer-focus-visible:ring-2 peer-focus-visible:ring-ring peer-disabled:opacity-60",
						)}
					>
						{t(`pages.people.growth.units.${option}`)}
					</span>
				</label>
			))}
		</div>
	);
}
