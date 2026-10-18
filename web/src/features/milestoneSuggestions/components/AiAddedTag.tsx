import { Sparkles } from "lucide-react";
import { useTranslation } from "react-i18next";

/**
 * Marks a Milestones album post that AI or an API token added without review.
 * Only circle admins get the data for it.
 */
export function AiAddedTag() {
	const { t } = useTranslation();
	const label = t("pages.circles.milestone_suggestions.ai_added");

	return (
		<span
			title={label}
			className="inline-flex shrink-0 items-center gap-1 self-center rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground"
		>
			<Sparkles className="size-3.5" aria-hidden="true" />
			{/* Phones show just the icon; the action row is full there. */}
			<span className="max-sm:sr-only">{label}</span>
		</span>
	);
}
