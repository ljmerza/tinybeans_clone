import { requireAuth } from "@/features/auth";
import { AlbumsRouteView } from "@/route-views/albums";
import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/albums/")({
	beforeLoad: requireAuth,
	component: AlbumsRouteView,
});
