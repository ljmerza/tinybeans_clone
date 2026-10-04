import { Link } from "@tanstack/react-router";
import { Fragment } from "react";
import { useTranslation } from "react-i18next";

import type { KeepPerson } from "../types";

export interface KeepPeopleProps {
	people: KeepPerson[] | undefined;
}

/**
 * "With Sophia · Grandma Jo": who is tagged on a post, each name linking to
 * their posts. Renders nothing when no one is tagged.
 */
export function KeepPeople({ people }: KeepPeopleProps) {
	const { t } = useTranslation();
	if (!people?.length) return null;

	return (
		<p className="text-sm text-muted-foreground">
			{t("pages.people.with")}{" "}
			{people.map((person, index) => (
				<Fragment key={person.id}>
					{index > 0 && " · "}
					<Link
						to="/people/$personId"
						params={{ personId: person.id }}
						className="font-medium text-foreground/80 hover:underline"
					>
						{person.name}
					</Link>
				</Fragment>
			))}
		</p>
	);
}
