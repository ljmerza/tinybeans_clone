import { apiClient as authApi } from "@/features/auth/api/authClient";
import { createApiClient } from "@/lib/api/client";
import type { ApiResponseWithMessages } from "@/types";
import type {
	CircleInvitationFinalizeResponse,
	CircleInvitationOnboardingStart,
	CircleOnboardingPayload,
	CircleSummary,
	CircleInvitationSummary,
	CircleMemberSummary,
	CircleMembershipSummary,
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

	getInvitations(circleId: number | string) {
		return authApi.get<
			ApiResponseWithMessages<{ invitations: CircleInvitationSummary[] }>
		>(`${USERS_BASE}/circles/${circleId}/invitations/`);
	},

	createInvitation(
		circleId: number | string,
		body: { email: string; role?: string },
	) {
		return authApi.post<
			ApiResponseWithMessages<{ invitation: CircleInvitationSummary }>
		>(`${USERS_BASE}/circles/${circleId}/invitations/`, body);
	},

	resendInvitation(circleId: number | string, invitationId: string) {
		return authApi.post<
			ApiResponseWithMessages<{ invitation: CircleInvitationSummary }>
		>(`${USERS_BASE}/circles/${circleId}/invitations/${invitationId}/resend/`, {});
	},

	cancelInvitation(circleId: number | string, invitationId: string) {
		return authApi.post<
			ApiResponseWithMessages<{ invitation: CircleInvitationSummary }>
		>(`${USERS_BASE}/circles/${circleId}/invitations/${invitationId}/cancel/`, {});
	},

	respondToInvitation(invitationId: string, action: "accept" | "decline") {
		return authApi.post<
			ApiResponseWithMessages<{ invitation: CircleInvitationSummary }>
		>(`${USERS_BASE}/invitations/${invitationId}/respond/`, {
			action,
		});
	},

	listMemberships() {
		return authApi.get<
			ApiResponseWithMessages<{ circles: CircleMembershipSummary[] }>
		>(`${USERS_BASE}/circles/`);
	},

	getCircleMembers(circleId: number | string) {
		return authApi.get<
			ApiResponseWithMessages<{
				circle: CircleSummary;
				members: CircleMemberSummary[];
			}>
		>(`${USERS_BASE}/circles/${circleId}/members/`);
	},

	removeMember(circleId: number | string, userId: number | string) {
		return authApi.delete<ApiResponseWithMessages>(
			`${USERS_BASE}/circles/${circleId}/members/${userId}/`,
		);
	},
};
