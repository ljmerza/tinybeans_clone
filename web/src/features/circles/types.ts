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
	id: number | string;
	email: string;
	display_name: string;
	first_name?: string | null;
	last_name?: string | null;
}

export type CircleInvitationStatus =
	| "pending"
	| "accepted"
	| "declined"
	| "cancelled"
	| "expired";

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

export interface CircleInvitationSummary {
	id: string;
	email: string;
	existing_user: boolean;
	role: string;
	status: CircleInvitationStatus;
	created_at: string;
	responded_at: string | null;
	reminder_sent_at: string | null;
	invited_user: CircleInvitationMemberSummary | null;
	invited_user_id?: number | string | null;
}

export interface CircleMembershipSummary {
	membership_id: number;
	circle: CircleSummary;
	role: string;
	created_at: string;
}

export interface CircleMemberSummary {
	membership_id: number;
	user: CircleUserSummary;
	role: string;
	created_at: string;
}

export interface CircleUserSummary {
	id: number;
	email: string;
	display_name: string;
	first_name?: string | null;
	last_name?: string | null;
	role: string;
	email_verified: boolean;
	date_joined: string;
	language: string | null;
	circle_onboarding_status: string | null;
	circle_onboarding_updated_at: string | null;
	needs_circle_onboarding: boolean;
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
