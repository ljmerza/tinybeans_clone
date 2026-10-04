import { requireAuth } from "@/features/auth";
import { PersonRouteView } from "@/route-views/people/detail";
import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/people/$personId")({
	beforeLoad: requireAuth,
	component: PersonRouteView,
});
