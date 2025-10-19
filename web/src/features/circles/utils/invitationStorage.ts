import type { CircleInvitationDetails } from "../types";

const STORAGE_KEY = "circle.invitation.onboarding";
const REQUEST_KEY_PREFIX = "circle.invitation.request.";
const STORAGE_EVENT = "circle-invitation-storage";

type InvitationStorageEvent = CustomEvent<StoredCircleInvitation | null>;

function emitInvitationStorage(payload: StoredCircleInvitation | null): void {
	if (typeof window === "undefined") return;
	try {
		const event: InvitationStorageEvent = new CustomEvent(STORAGE_EVENT, {
			detail: payload,
		});
		window.dispatchEvent(event);
	} catch (error) {
		console.warn("[circleInvitationStorage] Failed to dispatch storage event", error);
	}
}

export interface StoredCircleInvitation {
	onboardingToken: string;
	expiresInMinutes: number;
	invitation: CircleInvitationDetails;
	sourceToken?: string | null;
	redirectPath?: string | null;
}

function getRequestKey(token: string): string {
	return `${REQUEST_KEY_PREFIX}${token}`;
}

export function markInvitationRequest(token: string): void {
	if (typeof window === "undefined") return;
	try {
		window.sessionStorage.setItem(getRequestKey(token), Date.now().toString());
	} catch (error) {
		console.warn("[circleInvitationStorage] Failed to mark invitation request", error);
	}
}

export function clearInvitationRequest(token: string | null | undefined): void {
	if (typeof window === "undefined" || !token) return;
	try {
		window.sessionStorage.removeItem(getRequestKey(token));
	} catch (error) {
		console.warn("[circleInvitationStorage] Failed to clear invitation request", error);
	}
}

export function hasActiveInvitationRequest(token: string | null | undefined): boolean {
	if (typeof window === "undefined" || !token) return false;
	try {
		return window.sessionStorage.getItem(getRequestKey(token)) != null;
	} catch (error) {
		console.warn("[circleInvitationStorage] Failed to read invitation request flag", error);
		return false;
	}
}

export function saveInvitation(payload: StoredCircleInvitation): void {
	if (typeof window === "undefined") return;
	try {
		window.sessionStorage.setItem(
			STORAGE_KEY,
			JSON.stringify({
				...payload,
				sourceToken: payload.sourceToken ?? null,
				redirectPath: payload.redirectPath ?? null,
			}),
		);
		emitInvitationStorage({
			...payload,
			sourceToken: payload.sourceToken ?? null,
			redirectPath: payload.redirectPath ?? null,
		});
	} catch (error) {
		console.warn("[circleInvitationStorage] Failed to persist invitation token", error);
	}
}

export function loadInvitation(): StoredCircleInvitation | null {
	if (typeof window === "undefined") return null;
	try {
		const raw = window.sessionStorage.getItem(STORAGE_KEY);
		if (!raw) return null;
		const parsed = JSON.parse(raw) as Partial<StoredCircleInvitation>;
		if (
			!parsed ||
			typeof parsed.onboardingToken !== "string" ||
			typeof parsed.expiresInMinutes !== "number" ||
			!parsed.invitation
		) {
			return null;
		}
		return {
			onboardingToken: parsed.onboardingToken,
			expiresInMinutes: parsed.expiresInMinutes,
			invitation: parsed.invitation,
			sourceToken:
				typeof parsed.sourceToken === "string" ? parsed.sourceToken : null,
			redirectPath:
				typeof parsed.redirectPath === "string" ? parsed.redirectPath : null,
		};
	} catch (error) {
		console.warn("[circleInvitationStorage] Failed to read invitation token", error);
		return null;
	}
}

export function clearInvitation(): void {
	if (typeof window === "undefined") return;
	try {
		window.sessionStorage.removeItem(STORAGE_KEY);
		emitInvitationStorage(null);
	} catch (error) {
		console.warn("[circleInvitationStorage] Failed to clear invitation token", error);
	}
}

export type InvitationStorageListener = (
	payload: StoredCircleInvitation | null,
) => void;

export function subscribeInvitationStorage(
	listener: InvitationStorageListener,
): () => void {
	if (typeof window === "undefined") {
		return () => undefined;
	}

	const handler = (event: Event) => {
		const custom = event as InvitationStorageEvent;
		listener(custom.detail ?? null);
	};

	window.addEventListener(STORAGE_EVENT, handler as EventListener);
	return () => {
		window.removeEventListener(STORAGE_EVENT, handler as EventListener);
	};
}
