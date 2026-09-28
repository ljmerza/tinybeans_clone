import { requireAuth } from "@/features/auth";
import { FavoritesRouteView } from "@/route-views/favorites";
import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/favorites")({
	beforeLoad: requireAuth,
	component: FavoritesRouteView,
});
