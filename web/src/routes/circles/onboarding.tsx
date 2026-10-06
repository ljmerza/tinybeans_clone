import { requireAuth } from "@/features/auth";
import { createFileRoute } from "@tanstack/react-router";

import CircleOnboardingRoute from "@/route-views/circles/onboarding";

export const Route = createFileRoute("/circles/onboarding")({
	beforeLoad: async (args) => {
		// Open to anyone without a circle, including those who skipped it before.
		await requireAuth(args);
	},
	component: CircleOnboardingRoute,
});
