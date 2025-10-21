import { CircleDashboard } from "@/route-views/circles/dashboard";
import { createFileRoute } from "@tanstack/react-router";

function CircleDashboardRoute() {
	const { circleId } = Route.useParams();
	return <CircleDashboard circleId={circleId} />;
}

export const Route = createFileRoute("/circles/$circleId")({
	component: CircleDashboardRoute,
});
