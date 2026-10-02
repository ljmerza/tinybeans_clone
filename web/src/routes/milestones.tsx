import { requireAuth } from "@/features/auth";
import { MilestonesRouteView } from "@/route-views/milestones";
import { createFileRoute } from "@tanstack/react-router";

const UUID_PATTERN =
	/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export const Route = createFileRoute("/milestones")({
	beforeLoad: requireAuth,
	// A malformed child id falls back to everyone's milestones.
	validateSearch: (search: Record<string, unknown>): { child?: string } => ({
		child:
			typeof search.child === "string" && UUID_PATTERN.test(search.child)
				? search.child
				: undefined,
	}),
	component: MilestonesRouteView,
});
