import { EmailVerificationHandler } from "@/features/auth";
import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/verify-email")({
	component: VerifyEmailRoute,
	validateSearch: (search: Record<string, unknown>): { token?: string } => ({
		token: typeof search.token === "string" ? search.token : undefined,
	}),
});

function VerifyEmailRoute() {
	const { token } = Route.useSearch();
	return <EmailVerificationHandler token={token} />;
}
