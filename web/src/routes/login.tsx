import { requireGuest } from "@/features/auth";
import { createFileRoute } from "@tanstack/react-router";

import { LoginCard } from "@/features/auth";

export const Route = createFileRoute("/login")({
	beforeLoad: requireGuest,
	validateSearch: (search: Record<string, unknown>) => ({
		redirect: typeof search.redirect === "string" ? search.redirect : undefined,
	}),
	component: LoginRoute,
});

function LoginRoute() {
	const { redirect } = Route.useSearch();
	return <LoginCard redirect={redirect} />;
}
