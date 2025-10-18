import type { CircleInvitationDetails } from "../types";

const STORAGE_KEY = "circle.invitation.onboarding";

export interface StoredCircleInvitation {
	onboardingToken: string;
	expiresInMinutes: number;
	invitation: CircleInvitationDetails;
}

export function saveInvitation(payload: StoredCircleInvitation): void {
	if (typeof window === "undefined") return;
	try {
		window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
	} catch (error) {
		console.warn("[circleInvitationStorage] Failed to persist invitation token", error);
	}
}

export function loadInvitation(): StoredCircleInvitation | null {
	if (typeof window === "undefined") return null;
	try {
		const raw = window.sessionStorage.getItem(STORAGE_KEY);
		if (!raw) return null;
		return JSON.parse(raw) as StoredCircleInvitation;
	} catch (error) {
		console.warn("[circleInvitationStorage] Failed to read invitation token", error);
		return null;
	}
}

export function clearInvitation(): void {
	if (typeof window === "undefined") return;
	try {
		window.sessionStorage.removeItem(STORAGE_KEY);
	} catch (error) {
		console.warn("[circleInvitationStorage] Failed to clear invitation token", error);
	}
}
