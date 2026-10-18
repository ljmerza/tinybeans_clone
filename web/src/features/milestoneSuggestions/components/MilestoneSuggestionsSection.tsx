import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { KeepFeedPost } from "@/features/keeps/components/KeepFeedPost";
import { Check, X } from "lucide-react";
import { useId, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { PostAction } from "react-social-feed";

import {
	useApproveSuggestion,
	useDismissSuggestion,
	useMilestoneSuggestions,
} from "../hooks/useMilestoneSuggestions";
import type { MilestoneSuggestion } from "../types";

export interface MilestoneSuggestionsSectionProps {
	circleId: number;
}

/**
 * The "Suggested" row at the top of a circle's Milestones album: posts AI or
 * an API token picked while the circle reviews picks first, each with Add and
 * Dismiss. Hidden while nothing is pending; "Show dismissed" lists turned-down
 * ones so they can still be added. Only render it for circle admins.
 */
export function MilestoneSuggestionsSection({
	circleId,
}: MilestoneSuggestionsSectionProps) {
	const { t } = useTranslation();
	const ids = useId();
	const [showDismissed, setShowDismissed] = useState(false);
	const status = showDismissed ? "dismissed" : "pending";
	const suggestions = useMilestoneSuggestions(circleId, status);
	const approve = useApproveSuggestion(circleId);
	const dismiss = useDismissSuggestion(circleId);

	const items = useMemo(
		() =>
			(suggestions.data?.pages.flatMap((page) => page.results) ?? []).filter(
				(item) => item.keep !== null,
			),
		[suggestions.data],
	);
	const count = suggestions.data?.pages[0]?.count ?? 0;

	if (!showDismissed && (suggestions.isPending || count === 0)) return null;

	const busy = (item: MilestoneSuggestion) =>
		(approve.isPending && approve.variables === item.id) ||
		(dismiss.isPending && dismiss.variables === item.id);

	return (
		<section
			aria-labelledby={`${ids}-title`}
			className="mx-auto max-w-[var(--rsf-post-max-width)] space-y-4 rounded-lg border border-border bg-muted/30 p-3"
		>
			<div className="flex flex-wrap items-center justify-between gap-3">
				<div className="space-y-1">
					<h2
						id={`${ids}-title`}
						className="flex items-center gap-2 text-base font-semibold"
					>
						{showDismissed
							? t("pages.circles.milestone_suggestions.dismissed_title")
							: t("pages.circles.milestone_suggestions.title")}
						<Badge>{count}</Badge>
					</h2>
					<p className="text-sm text-muted-foreground">
						{showDismissed
							? t("pages.circles.milestone_suggestions.dismissed_description")
							: t("pages.circles.milestone_suggestions.description")}
					</p>
				</div>
				<div className="flex items-center gap-2">
					<Switch
						id={`${ids}-dismissed`}
						checked={showDismissed}
						onCheckedChange={setShowDismissed}
					/>
					<Label htmlFor={`${ids}-dismissed`}>
						{t("pages.circles.milestone_suggestions.show_dismissed")}
					</Label>
				</div>
			</div>

			{suggestions.isPending ? (
				<p className="text-sm text-muted-foreground">
					{t("pages.circles.milestone_suggestions.loading")}
				</p>
			) : suggestions.isError ? (
				<p className="text-sm text-destructive">
					{t("pages.circles.milestone_suggestions.load_failed")}
				</p>
			) : items.length === 0 ? (
				<p className="text-sm text-muted-foreground">
					{t("pages.circles.milestone_suggestions.dismissed_empty")}
				</p>
			) : (
				<ul className="space-y-4">
					{items.map((item) => (
						<li key={item.id} className="space-y-2">
							<SuggestionNote suggestion={item} />
							<KeepFeedPost
								keep={item.keep as NonNullable<MilestoneSuggestion["keep"]>}
								extraActions={
									<>
										<PostAction
											aria-label={t("pages.circles.milestone_suggestions.add")}
											title={t("pages.circles.milestone_suggestions.add")}
											disabled={busy(item)}
											icon={<Check strokeWidth={1.8} />}
											onClick={() => approve.mutate(item.id)}
										>
											<span aria-hidden="true" className="max-sm:hidden">
												{t("pages.circles.milestone_suggestions.add_short")}
											</span>
										</PostAction>
										{item.status === "pending" && (
											<PostAction
												aria-label={t(
													"pages.circles.milestone_suggestions.dismiss",
												)}
												title={t("pages.circles.milestone_suggestions.dismiss")}
												disabled={busy(item)}
												icon={<X strokeWidth={1.8} />}
												onClick={() => dismiss.mutate(item.id)}
											>
												<span aria-hidden="true" className="max-sm:hidden">
													{t(
														"pages.circles.milestone_suggestions.dismiss_short",
													)}
												</span>
											</PostAction>
										)}
									</>
								}
							/>
						</li>
					))}
				</ul>
			)}

			{suggestions.hasNextPage && (
				<div className="text-center">
					<Button
						type="button"
						variant="outline"
						size="sm"
						isLoading={suggestions.isFetchingNextPage}
						onClick={() =>
							void suggestions.fetchNextPage({ cancelRefetch: false })
						}
					>
						{t("pages.circles.milestone_suggestions.load_more")}
					</Button>
				</div>
			)}
		</section>
	);
}

/**
 * Who suggested it and why. The label and reason come from a model or an API
 * client, so they are only ever rendered as plain text.
 */
function SuggestionNote({ suggestion }: { suggestion: MilestoneSuggestion }) {
	const { t } = useTranslation();
	const source =
		suggestion.source === "agent"
			? t("pages.circles.milestone_suggestions.token_note", {
					prefix: suggestion.source_token_prefix,
				})
			: t("pages.circles.milestone_suggestions.ai_note");

	return (
		<div className="space-y-1 px-1 text-sm">
			{suggestion.label && <Badge variant="accent">{suggestion.label}</Badge>}
			<p className="text-muted-foreground">
				<span className="font-medium text-foreground">{source}</span>
				{suggestion.reason && <span>: {suggestion.reason}</span>}
			</p>
		</div>
	);
}
