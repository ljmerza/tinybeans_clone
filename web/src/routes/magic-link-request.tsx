import { requireGuest } from "@/features/auth";
import { createFileRoute } from "@tanstack/react-router";

import { MagicLinkRequestCard } from "@/features/auth";

export const Route = createFileRoute("/magic-link-request")({
	beforeLoad: requireGuest,
	validateSearch: (search: Record<string, unknown>) => ({
		redirect: typeof search.redirect === "string" ? search.redirect : undefined,
	}),
	component: MagicLinkRequestRoute,
});

function MagicLinkRequestRoute() {
	const { redirect } = Route.useSearch();
	return <MagicLinkRequestCard redirect={redirect} />;
}
