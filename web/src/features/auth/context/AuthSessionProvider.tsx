/**
 * Auth Session Context Provider
 * Provides stable auth state with differentiation between unknown, guest, and authenticated states
 */

import { useStore } from "@tanstack/react-store";
import { createContext, useContext, useEffect, useMemo } from "react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { useAuthSessionQuery } from "../hooks/useAuthSessionQuery";
import { authStore } from "../store/authStore";
import type { AuthUser } from "../types";

export type AuthStatus = "unknown" | "guest" | "authenticated";

export interface AuthSession {
	status: AuthStatus;
	accessToken: string | null;
	isAuthenticated: boolean;
	isGuest: boolean;
	isUnknown: boolean;
	user: AuthUser | null;
	isFetchingUser: boolean;
	userError: unknown;
	refetchUser: () => Promise<unknown>;
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
	const sessionQuery = useAuthSessionQuery({
		enabled: !isInitializing && Boolean(accessToken),
	});
	const { i18n } = useTranslation();

	useEffect(() => {
		if (isInitializing) return;
		const preferredLanguage = sessionQuery.data?.language;
		if (!preferredLanguage) return;
		if (preferredLanguage === i18n.language) return;

		void i18n.changeLanguage(preferredLanguage).catch((error) => {
			console.error("[AuthSession] Failed to sync language", error);
		});
	}, [i18n, isInitializing, sessionQuery.data?.language]);

	const session = useMemo<AuthSession>(() => {
		const status: AuthStatus = isInitializing
			? "unknown"
			: accessToken
				? "authenticated"
				: "guest";

		const user = sessionQuery.data ?? null;
		const userError = sessionQuery.error ?? null;

		return {
			status,
			accessToken,
			isAuthenticated: status === "authenticated",
			isGuest: status === "guest",
			isUnknown: status === "unknown",
			user,
			isFetchingUser: sessionQuery.isFetching,
			userError,
			refetchUser: sessionQuery.refetch,
		};
	}, [
		accessToken,
		isInitializing,
		sessionQuery.data,
		sessionQuery.isFetching,
		sessionQuery.error,
		sessionQuery.refetch,
	]);

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
