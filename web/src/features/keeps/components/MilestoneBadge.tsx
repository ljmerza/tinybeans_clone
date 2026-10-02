import { Link } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

import type { FeedMilestone } from "../types";
import { MILESTONE_EMOJI, describeMilestone } from "../utils/milestones";

export interface MilestoneBadgeProps {
	milestone: FeedMilestone;
}

/**
 * A post's milestone, e.g. "👣 First steps · Emma, 1 yr 2 mo". Links to the
 * milestones timeline, filtered to the child when there is one.
 */
export function MilestoneBadge({ milestone }: MilestoneBadgeProps) {
	const { t } = useTranslation();
	const label = describeMilestone(t, milestone);

	return (
		<Link
			to="/milestones"
			search={milestone.child ? { child: milestone.child.id } : {}}
			className="inline-flex max-w-full items-center gap-1.5 rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-medium text-primary transition-colors hover:bg-primary/15 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
			aria-label={t("milestones.badge_label", { milestone: label })}
		>
			<span aria-hidden="true">
				{MILESTONE_EMOJI[milestone.milestone_type]}
			</span>
			<span className="truncate">{label}</span>
		</Link>
	);
}
