import { useTranslation } from "react-i18next";

import { OnThisDayFrequencyToggle } from "./OnThisDayFrequencyToggle";

interface CircleOnThisDaySettingProps {
	circleId: number | string;
}

/**
 * The viewer's own "On this day" frequency for a circle, as a card on the
 * circle's settings page next to the monthly recap.
 */
export function CircleOnThisDaySetting({
	circleId,
}: CircleOnThisDaySettingProps) {
	const { t } = useTranslation();

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
			<OnThisDayFrequencyToggle circleId={circleId} />
		</div>
	);
}
