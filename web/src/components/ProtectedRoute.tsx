import { authStore } from "@/modules/login/store";
import { Navigate } from "@tanstack/react-router";
import { useStore } from "@tanstack/react-store";
import type { ReactNode } from "react";

interface ProtectedRouteProps {
	children: ReactNode;
	redirectTo?: string;
}

/**
 * ProtectedRoute component that ensures user is authenticated
 * Redirects to login page if no access token is found
 */
export function ProtectedRoute({
	children,
	redirectTo = "/login",
}: ProtectedRouteProps) {
	const { accessToken } = useStore(authStore);

	if (!accessToken) {
		return <Navigate to={redirectTo} />;
	}

	return <>{children}</>;
}
