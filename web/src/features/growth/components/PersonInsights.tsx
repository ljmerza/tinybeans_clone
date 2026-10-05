import type { PersonDetail } from "@/features/keeps/types";
import { GrowthSection } from "./GrowthSection";
import { PersonStatsSection } from "./PersonStatsSection";

export interface PersonInsightsProps {
	person: PersonDetail;
}

/** The top of the person page: their stats and, for a child, the growth log. */
export function PersonInsights({ person }: PersonInsightsProps) {
	return (
		<div className="space-y-3">
			<PersonStatsSection personId={person.id} name={person.name} />
			{person.kind === "child" && (
				<GrowthSection personId={person.id} name={person.name} />
			)}
		</div>
	);
}
