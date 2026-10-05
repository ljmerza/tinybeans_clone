import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { useTranslation } from "react-i18next";

import { useCircleRecapSettingMutation } from "../hooks/useCircleRecapSetting";

interface CircleRecapSettingProps {
	circleId: number | string;
	enabled: boolean;
}

/**
 * The monthly recap switch on a circle's settings page. Only render it for
 * circle admins.
 */
export function CircleRecapSetting({
	circleId,
	enabled,
}: CircleRecapSettingProps) {
	const { t } = useTranslation();
	const save = useCircleRecapSettingMutation(circleId);
	// Show the requested state while it saves, so the switch doesn't jump back.
	const checked = save.isPending ? save.variables : enabled;

	return (
		<div className="bg-card text-card-foreground border border-border rounded-lg shadow-md p-6">
			<div className="flex items-center justify-between gap-4">
				<div className="space-y-1">
					<Label htmlFor="circle-monthly-recap">
						{t("pages.circles.dashboard.recap.title")}
					</Label>
					<p className="text-sm text-muted-foreground">
						{t("pages.circles.dashboard.recap.description")}
					</p>
				</div>
				<Switch
					id="circle-monthly-recap"
					checked={checked}
					disabled={save.isPending}
					onCheckedChange={(next) => save.mutate(next)}
				/>
			</div>
		</div>
	);
}
