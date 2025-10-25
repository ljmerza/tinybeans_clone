import { requireAuth } from "@/features/auth";
import { createFileRoute } from "@tanstack/react-router";

import VerifyEmailRequiredRoute from "@/route-views/verify-email-required";

export const Route = createFileRoute("/verify-email-required")({
	beforeLoad: async (args) => {
		await requireAuth(args);
	},
	component: VerifyEmailRequiredRoute,
});
