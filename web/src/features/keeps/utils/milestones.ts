import type { TFunction } from "i18next";

import type { ChildAge, FeedMilestone, MilestoneType } from "../types";

/** Every milestone type, in the order the composer offers them. */
export const MILESTONE_TYPES: readonly MilestoneType[] = [
	"first_word",
	"first_steps",
	"first_tooth",
	"first_day_school",
	"birthday",
	"height_weight",
	"other",
];

export const MILESTONE_EMOJI: Record<MilestoneType, string> = {
	first_word: "💬",
	first_steps: "👣",
	first_tooth: "🦷",
	first_day_school: "🎒",
	birthday: "🎂",
	height_weight: "📏",
	other: "🎉",
};

/**
 * A short age: years and months once past one, then months, weeks, or days,
 * e.g. "1 yr 2 mo", "5 mo", "3 wks", "4 days".
 */
export function formatChildAge(
	t: TFunction,
	{ years, months, days }: ChildAge,
) {
	if (years > 0) {
		const yearPart = t("milestones.age.years", { count: years });
		return months > 0
			? `${yearPart} ${t("milestones.age.months", { count: months })}`
			: yearPart;
	}
	if (months > 0) return t("milestones.age.months", { count: months });
	if (days >= 7) {
		return t("milestones.age.weeks", { count: Math.floor(days / 7) });
	}
	return t("milestones.age.days", { count: days });
}

/**
 * "First steps · Emma, 1 yr 2 mo": the milestone, who it's for and their
 * age then, as far as each is known.
 */
export function describeMilestone(t: TFunction, milestone: FeedMilestone) {
	const type = t(`milestones.types.${milestone.milestone_type}`);
	const age = milestone.child_age
		? formatChildAge(t, milestone.child_age)
		: milestone.age_at_milestone;
	const who = milestone.child
		? [milestone.child.display_name, age].filter(Boolean).join(", ")
		: age;
	return who ? `${type} · ${who}` : type;
}
