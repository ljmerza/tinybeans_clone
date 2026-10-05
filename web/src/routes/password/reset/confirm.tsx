import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";

import { PasswordResetConfirmCard } from "@/features/auth";

// Open to signed-in users too: accounts without a password get this link from
// profile settings ("Set a password") and are usually still signed in.
export const Route = createFileRoute("/password/reset/confirm")({
	validateSearch: (search) =>
		z.object({ token: z.string().optional() }).parse(search),
	component: PasswordResetConfirmRoute,
});

function PasswordResetConfirmRoute() {
	const { token } = Route.useSearch();

	return <PasswordResetConfirmCard token={token} />;
}
