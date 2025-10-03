/**
 * Auth Session Context Provider
 * Provides stable auth state with differentiation between unknown, guest, and authenticated states
 */

import { useStore } from "@tanstack/react-store";
import { createContext, useContext, useMemo } from "react";
import type { ReactNode } from "react";
import { authStore } from "../store/authStore";

export type AuthStatus = "unknown" | "guest" | "authenticated";

export interface AuthSession {
	status: AuthStatus;
	accessToken: string | null;
	isAuthenticated: boolean;
	isGuest: boolean;
	isUnknown: boolean;
}

interface AuthSessionContextValue {
	session: AuthSession;
}

const AuthSessionContext = createContext<AuthSessionContextValue | null>(null);

interface AuthSessionProviderProps {
	children: ReactNode;
	isInitializing?: boolean;
}

/**
 * Provider that wraps the auth store with a stable React context
 */
export function AuthSessionProvider({
	children,
	isInitializing = false,
}: AuthSessionProviderProps) {
	const { accessToken } = useStore(authStore);

	const session = useMemo<AuthSession>(() => {
		const status: AuthStatus = isInitializing
			? "unknown"
			: accessToken
				? "authenticated"
				: "guest";

		return {
			status,
			accessToken,
			isAuthenticated: status === "authenticated",
			isGuest: status === "guest",
			isUnknown: status === "unknown",
		};
	}, [accessToken, isInitializing]);

	return (
		<AuthSessionContext.Provider value={{ session }}>
			{children}
		</AuthSessionContext.Provider>
	);
}

/**
 * Hook to access current auth session
 */
export function useAuthSession(): AuthSession {
	const context = useContext(AuthSessionContext);
	if (!context) {
		throw new Error("useAuthSession must be used within AuthSessionProvider");
	}
	return context.session;
}
