import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { X } from "lucide-react";
import { useId } from "react";
import { useTranslation } from "react-i18next";

import type { KeepChild, MilestoneType } from "../types";
import { MILESTONE_EMOJI, MILESTONE_TYPES } from "../utils/milestones";

/** Radix Select items can't have an empty value. */
const NO_CHILD = "none";

/** A milestone being picked in the composer; `type` is null until chosen. */
export interface MilestoneDraft {
	type: MilestoneType | null;
	childId: string | null;
}

export interface MilestoneFieldsProps {
	/** The file's name, for the fields' labels. */
	name: string;
	value: MilestoneDraft;
	/** Children of the post's circle; the child picker hides when empty. */
	childOptions: KeepChild[];
	disabled?: boolean;
	onChange: (value: MilestoneDraft) => void;
	onRemove: () => void;
}

/**
 * Which milestone a photo marks and, if the circle has children, whose.
 */
export function MilestoneFields({
	name,
	value,
	childOptions,
	disabled = false,
	onChange,
	onRemove,
}: MilestoneFieldsProps) {
	const { t } = useTranslation();
	const ids = useId();

	return (
		<div className="space-y-2 rounded-md bg-muted/50 p-2">
			<div className="flex items-center gap-2">
				<Label htmlFor={`${ids}-type`} className="sr-only">
					{t("pages.feed.new_post.milestone.type_label", { name })}
				</Label>
				<Select
					value={value.type ?? undefined}
					onValueChange={(type) =>
						onChange({ ...value, type: type as MilestoneType })
					}
					disabled={disabled}
				>
					<SelectTrigger
						id={`${ids}-type`}
						size="sm"
						className="min-w-0 flex-1 bg-background"
					>
						<SelectValue
							placeholder={t("pages.feed.new_post.milestone.type_placeholder")}
						/>
					</SelectTrigger>
					<SelectContent>
						{MILESTONE_TYPES.map((type) => (
							<SelectItem key={type} value={type}>
								<span aria-hidden="true">{MILESTONE_EMOJI[type]}</span>
								{type === "other"
									? t("pages.feed.new_post.milestone.other_type")
									: t(`milestones.types.${type}`)}
							</SelectItem>
						))}
					</SelectContent>
				</Select>
				{!disabled && (
					<Button
						type="button"
						variant="ghost"
						size="icon"
						className="size-7"
						aria-label={t("pages.feed.new_post.milestone.remove", { name })}
						onClick={onRemove}
					>
						<X aria-hidden="true" />
					</Button>
				)}
			</div>
			{childOptions.length > 0 && (
				<div>
					<Label htmlFor={`${ids}-child`} className="sr-only">
						{t("pages.feed.new_post.milestone.child_label", { name })}
					</Label>
					<Select
						value={value.childId ?? NO_CHILD}
						onValueChange={(childId) =>
							onChange({
								...value,
								childId: childId === NO_CHILD ? null : childId,
							})
						}
						disabled={disabled}
					>
						<SelectTrigger
							id={`${ids}-child`}
							size="sm"
							className="w-full bg-background"
						>
							<SelectValue />
						</SelectTrigger>
						<SelectContent>
							<SelectItem value={NO_CHILD}>
								{t("pages.feed.new_post.milestone.no_child")}
							</SelectItem>
							{childOptions.map((child) => (
								<SelectItem key={child.id} value={child.id}>
									{child.display_name}
								</SelectItem>
							))}
						</SelectContent>
					</Select>
				</div>
			)}
		</div>
	);
}
