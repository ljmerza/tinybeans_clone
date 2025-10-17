import { authApi } from "@/features/auth";
import type { ApiResponseWithMessages } from "@/types";

import type { CircleOnboardingPayload, CircleSummary } from "../types";

const USERS_BASE = "/users";

export function fetchCircleOnboarding() {
	return authApi.get<ApiResponseWithMessages<CircleOnboardingPayload>>(
		`${USERS_BASE}/circle-onboarding/`,
	);
}

export function skipCircleOnboarding() {
	return authApi.post<ApiResponseWithMessages<CircleOnboardingPayload>>(
		`${USERS_BASE}/circle-onboarding/skip/`,
		{},
	);
}

export function createCircle(body: { name: string }) {
	return authApi.post<ApiResponseWithMessages<{ circle: CircleSummary }>>(
		`${USERS_BASE}/circles/`,
		body,
	);
}
