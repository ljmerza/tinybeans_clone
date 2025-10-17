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
