import { apiClient as authApi } from "@/features/auth/api/authClient";
import { createApiClient } from "@/lib/api/client";
import type { ApiResponseWithMessages } from "@/types";
import type {
	CircleInvitationFinalizeResponse,
	CircleInvitationOnboardingStart,
	CircleOnboardingPayload,
	CircleSummary,
} from "../types";

const USERS_BASE = "/users";
const publicApi = createApiClient();

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

	startInvitationOnboarding(token: string) {
		return publicApi.post<
			ApiResponseWithMessages<CircleInvitationOnboardingStart>
		>(`${USERS_BASE}/invitations/accept/`, { token });
	},

	finalizeInvitation(onboardingToken: string) {
		return authApi.post<
			ApiResponseWithMessages<CircleInvitationFinalizeResponse>
		>(`${USERS_BASE}/invitations/finalize/`, {
			onboarding_token: onboardingToken,
		});
	},
};
