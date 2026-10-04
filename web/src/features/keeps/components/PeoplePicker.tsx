import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { UserRoundPlus } from "lucide-react";
import { useId, useState } from "react";
import { useTranslation } from "react-i18next";

import {
	personNameKey,
	useCirclePeople,
	useCreatePerson,
} from "../hooks/usePeople";
import type { KeepPerson } from "../types";

/** Matches the backend's `Person.name` max_length. */
const NAME_MAX_LENGTH = 150;

export interface PeoplePickerProps {
	circleId: number;
	/** Who is picked, in the order they were picked. */
	selected: KeepPerson[];
	onChange: (people: KeepPerson[]) => void;
	disabled?: boolean;
}

/**
 * Pick people from a circle by toggling their names, or type a new name to
 * add someone without a profile (e.g. "Grandma Jo") and pick them. Typing a
 * name that is already listed just picks that person.
 *
 * Not a <form>: it sits inside the post composer's form.
 */
export function PeoplePicker({
	circleId,
	selected,
	onChange,
	disabled = false,
}: PeoplePickerProps) {
	const { t } = useTranslation();
	const ids = useId();
	const people = useCirclePeople(circleId);
	const create = useCreatePerson();
	const [newName, setNewName] = useState("");

	const selectedIds = new Set(selected.map((person) => person.id));
	// Someone already picked stays visible even if the list no longer has them.
	const listed = people.data ?? [];
	const listedIds = new Set(listed.map((person) => person.id));
	const options: KeepPerson[] = [
		...listed,
		...selected.filter((person) => !listedIds.has(person.id)),
	];

	const toggle = (person: KeepPerson) =>
		onChange(
			selectedIds.has(person.id)
				? selected.filter((picked) => picked.id !== person.id)
				: [...selected, { id: person.id, name: person.name }],
		);

	const addSomeone = async () => {
		const name = newName.trim();
		if (!name || create.isPending) return;
		const existing = options.find(
			(person) => personNameKey(person.name) === personNameKey(name),
		);
		if (existing) {
			if (!selectedIds.has(existing.id)) toggle(existing);
			setNewName("");
			return;
		}
		try {
			const person = await create.mutateAsync({ circleId, name });
			onChange([...selected, { id: person.id, name: person.name }]);
			setNewName("");
		} catch {
			// The mutation's error toast explains it; the name stays to retry.
		}
	};

	return (
		<div className="space-y-2">
			{people.isPending ? (
				<p className="text-sm text-muted-foreground">
					{t("pages.people.picker.loading")}
				</p>
			) : people.isError ? (
				<div className="flex items-center gap-2">
					<p className="text-sm text-muted-foreground">
						{t("pages.people.picker.error")}
					</p>
					<Button
						type="button"
						variant="outline"
						size="sm"
						onClick={() => void people.refetch()}
					>
						{t("pages.feed.retry")}
					</Button>
				</div>
			) : options.length === 0 ? (
				<p className="text-sm text-muted-foreground">
					{t("pages.people.picker.empty")}
				</p>
			) : (
				<ul
					className="flex max-h-[40dvh] flex-wrap gap-1.5 overflow-y-auto"
					aria-label={t("pages.people.picker.list_label")}
				>
					{options.map((person) => {
						const picked = selectedIds.has(person.id);
						return (
							<li key={person.id}>
								<button
									type="button"
									aria-pressed={picked}
									disabled={disabled}
									onClick={() => toggle(person)}
									className={cn(
										"rounded-full border px-3 py-1 text-sm transition-colors disabled:opacity-50",
										picked
											? "border-primary bg-primary text-primary-foreground"
											: "hover:bg-muted",
									)}
								>
									{person.name}
								</button>
							</li>
						);
					})}
				</ul>
			)}

			<div className="flex gap-2">
				<label htmlFor={`${ids}-new`} className="sr-only">
					{t("pages.people.picker.add_label")}
				</label>
				<Input
					id={`${ids}-new`}
					value={newName}
					maxLength={NAME_MAX_LENGTH}
					placeholder={t("pages.people.picker.add_placeholder")}
					disabled={disabled}
					onChange={(event) => setNewName(event.target.value)}
					onKeyDown={(event) => {
						// Enter adds the name instead of submitting the composer.
						if (event.key !== "Enter") return;
						event.preventDefault();
						void addSomeone();
					}}
				/>
				<Button
					type="button"
					variant="outline"
					disabled={disabled || !newName.trim() || create.isPending}
					onClick={() => void addSomeone()}
				>
					<UserRoundPlus aria-hidden="true" />
					{t("pages.people.picker.add")}
				</Button>
			</div>
		</div>
	);
}
