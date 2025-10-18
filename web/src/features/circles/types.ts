import type { CircleOnboardingStatus } from "@/features/auth";

export interface CircleSummary {
	id: number;
	name: string;
	slug: string;
	member_count: number;
}

export interface CircleOnboardingPayload {
	status: CircleOnboardingStatus;
	needs_circle_onboarding: boolean;
	memberships_count: number;
	email_verified: boolean;
	email: string;
	updated_at: string | null;
}

export interface CircleInvitationMemberSummary {
	id: number;
	username: string;
	first_name?: string | null;
	last_name?: string | null;
}

export interface CircleInvitationDetails {
	id: string;
	email: string;
	existing_user: boolean;
	role: string;
	circle: CircleSummary;
	invited_user_id: number | null;
	invited_by: CircleInvitationMemberSummary | null;
	reminder_scheduled_at: string | null;
}

export interface CircleInvitationOnboardingStart {
	onboarding_token: string;
	expires_in_minutes: number;
	invitation: CircleInvitationDetails;
}

export interface CircleInvitationFinalizeResponse {
	circle: CircleSummary;
	membership: {
		membership_id: number;
		circle: CircleSummary;
		role: string;
		created_at: string;
	};
}

