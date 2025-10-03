import { requireGuest } from "@/features/auth";
import { createFileRoute } from "@tanstack/react-router";

import { MagicLinkRequestCard } from "@/features/auth";

export const Route = createFileRoute("/magic-link-request")({
	beforeLoad: requireGuest,
	component: MagicLinkRequestCard,
});
