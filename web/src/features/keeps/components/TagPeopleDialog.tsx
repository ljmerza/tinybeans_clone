import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { useSetKeepPeople } from "../hooks/useKeepFeed";
import type { FeedKeep, KeepPerson } from "../types";
import { PeoplePicker } from "./PeoplePicker";

export interface TagPeopleDialogProps {
	keep: FeedKeep;
	open: boolean;
	onOpenChange: (open: boolean) => void;
}

/**
 * Pick who is in a post; any member of its circle may. Nothing is saved until
 * Save. Mount it only while open, so the circle's people are fetched on demand
 * and the picks start from the post's current tags.
 */
export function TagPeopleDialog({
	keep,
	open,
	onOpenChange,
}: TagPeopleDialogProps) {
	const { t } = useTranslation();
	const setPeople = useSetKeepPeople();
	const [selected, setSelected] = useState<KeepPerson[]>(keep.people ?? []);

	const save = async () => {
		try {
			await setPeople.mutateAsync({ keep, people: selected });
			onOpenChange(false);
		} catch {
			// The mutation's error toast explains it; leave the dialog open to retry.
		}
	};

	return (
		<Dialog open={open} onOpenChange={onOpenChange}>
			<DialogContent className="max-w-sm" closeButtonLabel={t("common.close")}>
				<DialogHeader>
					<DialogTitle>{t("pages.people.tag.title")}</DialogTitle>
					<DialogDescription>
						{t("pages.people.tag.description", { circle: keep.circle.name })}
					</DialogDescription>
				</DialogHeader>

				<PeoplePicker
					circleId={keep.circle.id}
					selected={selected}
					onChange={setSelected}
					disabled={setPeople.isPending}
				/>

				<DialogFooter className="gap-2">
					<Button
						type="button"
						variant="ghost"
						onClick={() => onOpenChange(false)}
					>
						{t("common.cancel")}
					</Button>
					<Button
						type="button"
						disabled={setPeople.isPending}
						onClick={() => void save()}
					>
						{setPeople.isPending
							? t("pages.people.tag.saving")
							: t("pages.people.tag.save")}
					</Button>
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}
