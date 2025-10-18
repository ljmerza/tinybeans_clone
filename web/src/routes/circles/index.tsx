import { CirclesIndexRouteView } from "@/route-views/circles/index";
import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/circles/")({
  component: CirclesIndexRouteView,
});
