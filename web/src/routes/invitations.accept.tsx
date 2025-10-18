import { createFileRoute } from "@tanstack/react-router";

import InvitationAcceptRouteView from "@/route-views/invitations/accept";

export const Route = createFileRoute("/invitations/accept")({
	component: InvitationAcceptRouteView,
	validateSearch: (search: Record<string, unknown>) => ({
		token: (search.token as string) || undefined,
	}),
});
