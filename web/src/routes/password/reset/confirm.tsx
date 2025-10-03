import { requireGuest } from "@/features/auth";
import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";

import { PasswordResetConfirmCard } from "@/features/auth";

export const Route = createFileRoute("/password/reset/confirm")({
	beforeLoad: requireGuest,
	validateSearch: (search) =>
		z.object({ token: z.string().optional() }).parse(search),
	component: PasswordResetConfirmRoute,
});

function PasswordResetConfirmRoute() {
	const { token } = Route.useSearch();

	return <PasswordResetConfirmCard token={token} />;
}
