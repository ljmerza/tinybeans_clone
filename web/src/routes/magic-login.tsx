import { createFileRoute } from "@tanstack/react-router";

import { MagicLoginHandler } from "@/features/auth";

export const Route = createFileRoute("/magic-login")({
	component: MagicLoginRoute,
	validateSearch: (
		search: Record<string, unknown>,
	): { token?: string; redirect?: string } => ({
		token: typeof search.token === "string" ? search.token : undefined,
		redirect: typeof search.redirect === "string" ? search.redirect : undefined,
	}),
});

function MagicLoginRoute() {
	const { token, redirect } = Route.useSearch();
	return <MagicLoginHandler token={token} redirect={redirect} />;
}
