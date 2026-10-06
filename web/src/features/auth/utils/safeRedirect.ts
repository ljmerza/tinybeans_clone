/**
 * The path to follow for a `?redirect=` target, or null when it would leave
 * this site. The target comes from the URL, so anyone can craft it; without
 * this, `/login?redirect=https://evil.example` sends people off-site after
 * signing in.
 */
export function safeRedirectPath(target?: string | null): string | null {
	if (!target || typeof window === "undefined") return null;
	try {
		const url = new URL(target, window.location.origin);
		if (url.origin !== window.location.origin) return null;
		return `${url.pathname}${url.search}${url.hash}`;
	} catch {
		return null;
	}
}
