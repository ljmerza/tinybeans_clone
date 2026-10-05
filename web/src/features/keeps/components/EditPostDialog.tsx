import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useId, useState } from "react";
import { useTranslation } from "react-i18next";

import { memoryDay, useUpdateKeep } from "../hooks/useKeepFeed";
import type { FeedKeep, KeepPerson } from "../types";
import { PeoplePicker } from "./PeoplePicker";

/** Matches the backend's `Keep.title` max_length. */
const TITLE_MAX_LENGTH = 255;

/** `YYYY-MM-DD` for today in the viewer's own timezone. */
function localToday() {
	const now = new Date();
	const month = String(now.getMonth() + 1).padStart(2, "0");
	const day = String(now.getDate()).padStart(2, "0");
	return `${now.getFullYear()}-${month}-${day}`;
}

export interface EditPostDialogProps {
	keep: FeedKeep;
	open: boolean;
	onOpenChange: (open: boolean) => void;
}

/**
 * Change a post's title, caption, date and people; only its creator or a
 * circle admin may. Nothing is saved until Save. Mount it only while open, so
 * the fields start from the post as it is now.
 */
export function EditPostDialog({
	keep,
	open,
	onOpenChange,
}: EditPostDialogProps) {
	const { t } = useTranslation();
	const ids = useId();
	const update = useUpdateKeep();
	const originalDay = memoryDay(keep.date_of_memory);
	const [title, setTitle] = useState(keep.title);
	const [description, setDescription] = useState(keep.description);
	const [date, setDate] = useState(originalDay);
	const [people, setPeople] = useState<KeepPerson[]>(keep.people ?? []);

	const today = localToday();
	const canSave = date !== "" && !update.isPending;

	const handleSubmit = async (event: React.FormEvent) => {
		event.preventDefault();
		if (!canSave) return;
		try {
			await update.mutateAsync({
				keep,
				title: title.trim(),
				description: description.trim(),
				// A new day keeps the memory's time of day, so posts from one day
				// stay in order.
				...(date !== originalDay && {
					date_of_memory: `${date}${new Date(keep.date_of_memory).toISOString().slice(10)}`,
				}),
				people,
			});
			onOpenChange(false);
		} catch {
			// The mutation's error toast explains it; leave the dialog open to retry.
		}
	};

	return (
		<Dialog open={open} onOpenChange={onOpenChange}>
			<DialogContent
				className="max-h-[90dvh] max-w-md overflow-y-auto"
				closeButtonLabel={t("common.close")}
			>
				<DialogHeader>
					<DialogTitle>{t("pages.feed.edit_post.title")}</DialogTitle>
					<DialogDescription>
						{t("pages.feed.edit_post.description")}
					</DialogDescription>
				</DialogHeader>
				<form className="space-y-4" onSubmit={handleSubmit}>
					<div className="space-y-1.5">
						<Label htmlFor={`${ids}-title`}>
							{t("pages.feed.edit_post.post_title")}
						</Label>
						<Input
							id={`${ids}-title`}
							value={title}
							maxLength={TITLE_MAX_LENGTH}
							placeholder={t("pages.feed.edit_post.title_placeholder")}
							onChange={(event) => setTitle(event.target.value)}
							disabled={update.isPending}
						/>
					</div>
					<div className="space-y-1.5">
						<Label htmlFor={`${ids}-caption`}>
							{t("pages.feed.edit_post.caption")}
						</Label>
						<Textarea
							id={`${ids}-caption`}
							value={description}
							rows={3}
							placeholder={t("pages.feed.edit_post.caption_placeholder")}
							onChange={(event) => setDescription(event.target.value)}
							disabled={update.isPending}
						/>
					</div>
					<div className="space-y-1.5">
						<Label htmlFor={`${ids}-date`}>
							{t("pages.feed.edit_post.date")}
						</Label>
						<Input
							id={`${ids}-date`}
							type="date"
							value={date}
							required
							// Never later than today, unless the post already is.
							max={originalDay > today ? originalDay : today}
							onChange={(event) => setDate(event.target.value)}
							disabled={update.isPending}
						/>
					</div>
					<fieldset className="space-y-1.5">
						<legend className="mb-1.5 text-sm font-medium leading-none">
							{t("pages.feed.edit_post.people")}
						</legend>
						<PeoplePicker
							circleId={keep.circle.id}
							selected={people}
							onChange={setPeople}
							disabled={update.isPending}
						/>
					</fieldset>
					<DialogFooter className="gap-2">
						<Button
							type="button"
							variant="ghost"
							onClick={() => onOpenChange(false)}
						>
							{t("common.cancel")}
						</Button>
						<Button type="submit" disabled={!canSave}>
							{update.isPending
								? t("pages.feed.edit_post.saving")
								: t("pages.feed.edit_post.save")}
						</Button>
					</DialogFooter>
				</form>
			</DialogContent>
		</Dialog>
	);
}
