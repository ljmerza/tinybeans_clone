import { requireGuest } from "@/features/auth";
import { createFileRoute } from "@tanstack/react-router";

import { SignupCard } from "@/features/auth";

export const Route = createFileRoute("/signup")({
	beforeLoad: requireGuest,
	validateSearch: (search: Record<string, unknown>) => ({
		redirect: typeof search.redirect === "string" ? search.redirect : undefined,
		email: typeof search.email === "string" ? search.email : undefined,
	}),
	component: SignupRoute,
});

function SignupRoute() {
	const { redirect, email } = Route.useSearch();
	return <SignupCard redirect={redirect} prefillEmail={email} />;
}
