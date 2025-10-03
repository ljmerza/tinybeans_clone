import { PublicOnlyRoute } from "@/components";
import { createFileRoute } from "@tanstack/react-router";

import { PasswordResetRequestCard } from "@/features/auth";

export const Route = createFileRoute("/password/reset/request")({
	component: () => (
		<PublicOnlyRoute redirectTo="/">
			<PasswordResetRequestCard />
		</PublicOnlyRoute>
	),
});
