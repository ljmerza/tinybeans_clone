import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { useTranslation } from "react-i18next";

import { useCircleMilestoneReviewSettingMutation } from "../hooks/useCircleMilestoneReviewSetting";

interface CircleMilestoneReviewSettingProps {
	circleId: number | string;
	enabled: boolean;
}

/**
 * The "review AI milestone picks" switch on a circle's settings page. While
 * it is on, picks from in-app AI and API tokens wait in the Milestones
 * album's Suggested row; while off they go straight into the album. Only
 * render it for circle admins.
 */
export function CircleMilestoneReviewSetting({
	circleId,
	enabled,
}: CircleMilestoneReviewSettingProps) {
	const { t } = useTranslation();
	const save = useCircleMilestoneReviewSettingMutation(circleId);
	// Show the requested state while it saves, so the switch doesn't jump back.
	const checked = save.isPending ? save.variables : enabled;

	return (
		<div className="bg-card text-card-foreground border border-border rounded-lg shadow-md p-6">
			<div className="flex items-center justify-between gap-4">
				<div className="space-y-1">
					<Label htmlFor="circle-milestone-review">
						{t("pages.circles.dashboard.milestone_review.title")}
					</Label>
					<p className="text-sm text-muted-foreground">
						{t("pages.circles.dashboard.milestone_review.description")}
					</p>
				</div>
				<Switch
					id="circle-milestone-review"
					checked={checked}
					disabled={save.isPending}
					onCheckedChange={(next) => save.mutate(next)}
				/>
			</div>
		</div>
	);
}
