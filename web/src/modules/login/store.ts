import { Store } from "@tanstack/store";

// Store token only in memory (not in localStorage)
// This ensures that when the token refresh fails, the user is logged out
export const authStore = new Store({
	accessToken: null as string | null,
});

export function setAccessToken(token: string | null) {
	authStore.setState((s) => ({ ...s, accessToken: token }));
}
