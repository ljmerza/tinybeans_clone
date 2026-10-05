import { LoadingState } from "@/components";
import { Link } from "@tanstack/react-router";
import { Heart, ImageIcon } from "lucide-react";
import { useTranslation } from "react-i18next";

import { usePersonStats } from "../hooks/useGrowth";
import type { PersonStats, PersonStatsPost } from "../types";
import { BarChart } from "./charts";

function Tile({ label, value }: { label: string; value: string }) {
	return (
		<div className="min-w-0 rounded-md bg-muted/60 px-3 py-2">
			<dt className="text-xs text-muted-foreground">{label}</dt>
			<dd className="truncate text-base font-semibold">{value}</dd>
		</div>
	);
}

function PostLink({
	heading,
	post,
	locale,
}: {
	heading: string;
	post: PersonStatsPost;
	locale: string;
}) {
	const { t } = useTranslation();
	const date = new Date(post.date_of_memory).toLocaleDateString(locale, {
		timeZone: "UTC",
		year: "numeric",
		month: "short",
		day: "numeric",
	});
	return (
		<Link
			to="/keeps/$keepId"
			params={{ keepId: post.id }}
			className="flex min-w-0 items-center gap-3 rounded-md p-1.5 hover:bg-muted"
		>
			{post.thumbnail_url ? (
				<img
					src={post.thumbnail_url}
					alt=""
					className="size-12 shrink-0 rounded object-cover"
					loading="lazy"
				/>
			) : (
				<span className="flex size-12 shrink-0 items-center justify-center rounded bg-muted text-muted-foreground">
					<ImageIcon className="size-5" aria-hidden="true" />
				</span>
			)}
			<span className="min-w-0">
				<span className="block text-xs text-muted-foreground">{heading}</span>
				<span className="block truncate text-sm font-medium">
					{post.title || t("pages.people.stats.untitled")}
				</span>
				<span className="flex items-center gap-1 text-xs text-muted-foreground">
					{date}
					{post.like_count ? (
						<>
							{" · "}
							<Heart className="size-3" aria-hidden="true" />
							{t("pages.people.stats.likes", { count: post.like_count })}
						</>
					) : null}
				</span>
			</span>
		</Link>
	);
}

/** "2 years, 1 month", "5 months, 3 days" or "12 days". */
function useFormatAge() {
	const { t } = useTranslation();
	return ({ years, months, days }: NonNullable<PersonStats["age"]>) => {
		const parts =
			years > 0
				? [
						t("pages.people.stats.age.years", { count: years }),
						months > 0 && t("pages.people.stats.age.months", { count: months }),
					]
				: months > 0
					? [
							t("pages.people.stats.age.months", { count: months }),
							days > 0 && t("pages.people.stats.age.days", { count: days }),
						]
					: [t("pages.people.stats.age.days", { count: days })];
		return parts.filter(Boolean).join(", ");
	};
}

export interface PersonStatsSectionProps {
	personId: string;
	name: string;
}

/**
 * At-a-glance numbers for a person: age (children with a birthdate), how many
 * posts and photos they're in, posts per month over the last year, and their
 * first and most-liked posts.
 */
export function PersonStatsSection({
	personId,
	name,
}: PersonStatsSectionProps) {
	const { t, i18n } = useTranslation();
	const locale = i18n.resolvedLanguage ?? "en";
	const formatAge = useFormatAge();
	const { data: stats, isLoading, error } = usePersonStats(personId);

	if (isLoading) {
		return (
			<LoadingState
				layout="inline"
				spinnerSize="sm"
				className="justify-center py-4 text-sm text-muted-foreground"
				message={t("pages.people.stats.loading")}
			/>
		);
	}
	// The posts below still show, so a failed stats load stays quiet.
	if (error || !stats) return null;

	const monthName = (month: string, style: "narrow" | "long") =>
		new Date(`${month}-01T00:00:00Z`).toLocaleDateString(locale, {
			timeZone: "UTC",
			month: style,
			...(style === "long" ? { year: "numeric" } : {}),
		});
	const bars = stats.posts_per_month.map(({ month, count }) => ({
		key: month,
		value: count,
		tick: monthName(month, "narrow"),
		label: t("pages.people.stats.month_posts", {
			month: monthName(month, "long"),
			count,
		}),
	}));

	return (
		<section
			aria-labelledby={`stats-${personId}`}
			className="space-y-4 rounded-lg border border-border bg-card p-4 text-card-foreground"
		>
			<h2 id={`stats-${personId}`} className="text-base font-semibold">
				{t("pages.people.stats.title")}
			</h2>
			<dl className="grid grid-cols-2 gap-2 sm:grid-cols-3">
				{stats.age && (
					<Tile
						label={t("pages.people.stats.age_label")}
						value={formatAge(stats.age)}
					/>
				)}
				<Tile
					label={t("pages.people.stats.posts")}
					value={stats.post_count.toLocaleString(locale)}
				/>
				<Tile
					label={
						stats.video_count > 0
							? t("pages.people.stats.photos_and_videos")
							: t("pages.people.stats.photos")
					}
					value={
						stats.video_count > 0
							? `${stats.photo_count.toLocaleString(locale)} · ${stats.video_count.toLocaleString(locale)}`
							: stats.photo_count.toLocaleString(locale)
					}
				/>
			</dl>

			{stats.post_count > 0 && (
				<div className="space-y-1">
					<h3 className="text-sm font-medium">
						{t("pages.people.stats.per_month_title")}
					</h3>
					<BarChart
						bars={bars}
						ariaLabel={t("pages.people.stats.per_month_label", { name })}
					/>
					<ul className="sr-only">
						{bars.map((bar) => (
							<li key={bar.key}>{bar.label}</li>
						))}
					</ul>
				</div>
			)}

			{(stats.first_post || stats.most_liked_post) && (
				<div className="grid gap-1 sm:grid-cols-2">
					{stats.first_post && (
						<PostLink
							heading={t("pages.people.stats.first_post")}
							post={stats.first_post}
							locale={locale}
						/>
					)}
					{stats.most_liked_post && (
						<PostLink
							heading={t("pages.people.stats.most_liked_post")}
							post={stats.most_liked_post}
							locale={locale}
						/>
					)}
				</div>
			)}
		</section>
	);
}
