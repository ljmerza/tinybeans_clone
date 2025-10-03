import { PublicOnlyRoute } from "@/components";
import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";

import { PasswordResetConfirmCard } from "@/features/auth";

export const Route = createFileRoute("/password/reset/confirm")({
	validateSearch: (search) =>
		z.object({ token: z.string().optional() }).parse(search),
	component: PasswordResetConfirmRoute,
});

function PasswordResetConfirmRoute() {
	const { token } = Route.useSearch();

	return (
		<PublicOnlyRoute redirectTo="/">
			<PasswordResetConfirmCard token={token} />
		</PublicOnlyRoute>
	);
}
