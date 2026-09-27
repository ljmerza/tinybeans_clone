import { requireAuth } from "@/features/auth";
import { KeepDetailRouteView } from "@/route-views/keeps/detail";
import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/keeps/$keepId")({
	beforeLoad: requireAuth,
	component: KeepDetailRouteView,
});
