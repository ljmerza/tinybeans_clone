import { createFileRoute } from "@tanstack/react-router";

import { MagicLinkRequestCard } from "@/features/auth";

export const Route = createFileRoute("/magic-link-request")({
	component: MagicLinkRequestCard,
});
