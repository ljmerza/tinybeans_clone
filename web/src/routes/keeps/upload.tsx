import { createFileRoute } from "@tanstack/react-router";
import { CircleMediaUploadView } from "@/route-views/keeps/media-upload";

export const Route = createFileRoute("/keeps/upload")({
	component: CircleMediaUploadView,
});
