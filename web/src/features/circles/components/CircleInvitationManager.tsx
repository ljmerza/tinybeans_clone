import { CircleInvitationForm } from "./CircleInvitationForm";
import { CircleInvitationList } from "./CircleInvitationList";

interface CircleInvitationManagerProps {
	circleId: number | string;
	layout?: "grid" | "stack";
}

export function CircleInvitationManager({
	circleId,
	layout = "grid",
}: CircleInvitationManagerProps) {
	const className =
		layout === "grid"
			? "grid gap-6 lg:grid-cols-2"
			: "flex flex-col gap-6";

	return (
		<div className={className}>
			<CircleInvitationForm circleId={circleId} />
			<CircleInvitationList circleId={circleId} />
		</div>
	);
}
