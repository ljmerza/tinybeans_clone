import { apiClient as authApi } from "@/features/auth/api/authClient";
import type { ApiResponseWithMessages } from "@/types";
import type { CircleOnboardingPayload, CircleSummary } from "../types";

const USERS_BASE = "/users";

export const circleServices = {
	getOnboarding() {
		return authApi.get<ApiResponseWithMessages<CircleOnboardingPayload>>(
			`${USERS_BASE}/circle-onboarding/`,
		);
	},

	skipOnboarding() {
		return authApi.post<ApiResponseWithMessages<CircleOnboardingPayload>>(
			`${USERS_BASE}/circle-onboarding/skip/`,
			{},
		);
	},

	createCircle(body: { name: string }) {
		return authApi.post<ApiResponseWithMessages<{ circle: CircleSummary }>>(
			`${USERS_BASE}/circles/`,
			body,
		);
	},
};
