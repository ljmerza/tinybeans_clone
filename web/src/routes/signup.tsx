import { requireGuest } from "@/features/auth";
import { createFileRoute } from "@tanstack/react-router";

import { SignupCard } from "@/features/auth";

export const Route = createFileRoute("/signup")({
	beforeLoad: requireGuest,
	validateSearch: (search: Record<string, unknown>) => ({
		redirect: typeof search.redirect === "string" ? search.redirect : undefined,
	}),
	component: SignupRoute,
});

function SignupRoute() {
	const { redirect } = Route.useSearch();
	return <SignupCard redirect={redirect} />;
}
