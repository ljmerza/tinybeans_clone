/**
 * Auth Query Keys
 * Centralized factory for TanStack Query auth-related keys.
 */

const authRoot = ["auth"] as const;
const userRoot = ["user"] as const;

export const authKeys = {
	all: () => authRoot,
	session: () => [...authRoot, "session"] as const,
	status: () => [...authRoot, "status"] as const,
};

export const userKeys = {
	all: () => userRoot,
	profile: () => [...userRoot, "profile"] as const,
};
