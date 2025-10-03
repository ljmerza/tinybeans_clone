import { createFileRoute } from "@tanstack/react-router";

import { MagicLoginHandler } from "@/features/auth";

export const Route = createFileRoute("/magic-login")({
	component: MagicLoginRoute,
	validateSearch: (search: Record<string, unknown>) => ({
		token: (search.token as string) || undefined,
	}),
});

function MagicLoginRoute() {
	const { token } = Route.useSearch();
	return <MagicLoginHandler token={token} />;
}
