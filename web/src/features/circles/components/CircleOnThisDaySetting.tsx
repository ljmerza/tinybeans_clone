import { toOnThisDayFrequency } from "@/features/keeps/utils/onThisDay";
import { useTranslation } from "react-i18next";

import { useCircleOnThisDaySettingMutation } from "../hooks/useCircleOnThisDaySetting";
import { OnThisDayFrequencyToggle } from "./OnThisDayFrequencyToggle";

interface CircleOnThisDaySettingProps {
	circleId: number | string;
	/** The circle's current setting; missing means "normal". */
	frequency?: string;
}

/**
 * How often a circle's "On this day" cards show in every member's home feed,
 * on the circle's settings page next to the monthly recap. Only render it for
 * circle admins.
 */
export function CircleOnThisDaySetting({
	circleId,
	frequency,
}: CircleOnThisDaySettingProps) {
	const { t } = useTranslation();
	const save = useCircleOnThisDaySettingMutation(circleId);
	// Show the requested choice while it saves, so the switch doesn't jump back.
	const value = save.isPending
		? save.variables
		: toOnThisDayFrequency(frequency);

	return (
		<div className="bg-card text-card-foreground border border-border rounded-lg shadow-md p-6 space-y-4">
			<div className="space-y-1">
				<h3 className="text-sm font-medium leading-none">
					{t("pages.circles.dashboard.on_this_day.title")}
				</h3>
				<p className="text-sm text-muted-foreground">
					{t("pages.circles.dashboard.on_this_day.description")}
				</p>
			</div>
			<OnThisDayFrequencyToggle
				value={value}
				disabled={save.isPending}
				onChange={(next) => {
					if (next !== value) save.mutate(next);
				}}
			/>
		</div>
	);
}
