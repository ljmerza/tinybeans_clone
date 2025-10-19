type AnalyticsPayload = Record<string, unknown> | undefined;

declare global {
	interface Window {
		tinybeansAnalytics?: {
			track: (event: string, payload?: AnalyticsPayload) => void;
		};
		dataLayer?: Array<Record<string, unknown>>;
	}
}

/**
 * Track circle invitation funnel events using the active analytics integrations.
 * Falls back to console.debug when no integrations are registered.
 */
export function trackCircleInviteEvent(
	event: string,
	payload?: AnalyticsPayload,
): void {
	if (typeof window === "undefined") return;

	try {
		if (window.tinybeansAnalytics?.track) {
			window.tinybeansAnalytics.track(event, payload);
			return;
		}

		if (Array.isArray(window.dataLayer)) {
			window.dataLayer.push({
				event,
				...(payload ?? {}),
				timestamp: new Date().toISOString(),
			});
			return;
		}

		// Development fallback
		// eslint-disable-next-line no-console
		console.debug(`[analytics] ${event}`, payload ?? {});
	} catch (error) {
		// eslint-disable-next-line no-console
		console.warn("[analytics] Failed to record invite event", error);
	}
}

/**
 * Convenience helper for storing redirect paths ahead of auth flows.
 */
const INVITE_REDIRECT_KEY = "circle.invitation.redirect";

export function rememberInviteRedirect(path: string | null): void {
	if (typeof window === "undefined") return;
	try {
		if (!path) {
			window.sessionStorage.removeItem(INVITE_REDIRECT_KEY);
			return;
		}
		window.sessionStorage.setItem(INVITE_REDIRECT_KEY, path);
	} catch (error) {
		// eslint-disable-next-line no-console
		console.warn("[analytics] Failed to persist invite redirect", error);
	}
}

export function consumeInviteRedirect(): string | null {
	if (typeof window === "undefined") return null;
	try {
		const value = window.sessionStorage.getItem(INVITE_REDIRECT_KEY);
		if (value) {
			window.sessionStorage.removeItem(INVITE_REDIRECT_KEY);
		}
		return value;
	} catch (error) {
		// eslint-disable-next-line no-console
		console.warn("[analytics] Failed to read invite redirect", error);
		return null;
	}
}

export function parseInvitationRedirect(
	target?: string | null,
): { token?: string; onboardingToken?: string } | null {
	if (!target || typeof window === "undefined") {
		return null;
	}

	try {
		const url = new URL(target, window.location.origin);
		if (url.pathname === "/invitations/accept") {
			return {
				token: url.searchParams.get("token") ?? undefined,
				onboardingToken: url.searchParams.get("onboarding") ?? undefined,
			};
		}
		return null;
	} catch (error) {
		// eslint-disable-next-line no-console
		console.warn("[analytics] Failed to parse invitation redirect", error);
		return null;
	}
}
