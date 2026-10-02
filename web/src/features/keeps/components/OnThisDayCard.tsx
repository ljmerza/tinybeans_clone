import { History } from "lucide-react";
import { useId } from "react";
import { useTranslation } from "react-i18next";

import type { FeedKeep } from "../types";
import { KeepFeedPost } from "./KeepFeedPost";

export interface OnThisDayCardProps {
	keep: FeedKeep;
	/** Whole years since the memory; at least 1. */
	yearsAgo: number;
}

/**
 * A post from this day in an earlier year, shown in the home feed under an
 * "On this day · N years ago" label.
 */
export function OnThisDayCard({ keep, yearsAgo }: OnThisDayCardProps) {
	const { t } = useTranslation();
	const labelId = useId();

	return (
		<section
			aria-labelledby={labelId}
			className="mx-auto max-w-[var(--rsf-post-max-width)]"
		>
			<p
				id={labelId}
				className="mb-2 flex items-center gap-1.5 px-1 text-sm font-semibold text-primary"
			>
				<History aria-hidden="true" className="size-4 shrink-0" />
				{t("pages.feed.on_this_day")}
				<span className="font-normal text-muted-foreground">
					· {t("pages.feed.on_this_day_years_ago", { count: yearsAgo })}
				</span>
			</p>
			<KeepFeedPost keep={keep} />
		</section>
	);
}
