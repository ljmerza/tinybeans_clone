import { requireAuth } from "@/features/auth";
import { createFileRoute } from "@tanstack/react-router";

import CircleOnboardingRoute from "@/route-views/circles/onboarding";

export const Route = createFileRoute("/circles/onboarding")({
	beforeLoad: requireAuth,
	component: CircleOnboardingRoute,
});
