import {
	requireAuth,
	requireCircleOnboardingIncomplete,
} from "@/features/auth";
import { createFileRoute } from "@tanstack/react-router";

import CircleOnboardingRoute from "@/route-views/circles/onboarding";

export const Route = createFileRoute("/circles/onboarding")({
	beforeLoad: async (args) => {
		await requireAuth(args);
		await requireCircleOnboardingIncomplete(args);
	},
	component: CircleOnboardingRoute,
});
