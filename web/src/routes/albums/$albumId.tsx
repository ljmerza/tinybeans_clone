import { requireAuth } from "@/features/auth";
import { AlbumRouteView } from "@/route-views/albums/detail";
import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/albums/$albumId")({
	beforeLoad: requireAuth,
	component: AlbumRouteView,
});
