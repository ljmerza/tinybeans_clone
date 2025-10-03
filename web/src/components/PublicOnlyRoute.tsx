import { authStore } from "@/features/auth";
import { Navigate } from "@tanstack/react-router";
import { useStore } from "@tanstack/react-store";
import type { ReactNode } from "react";

interface PublicOnlyRouteProps {
	children: ReactNode;
	redirectTo?: string;
}

/**
 * Ensures that authenticated users are redirected away from public-only routes.
 */
export function PublicOnlyRoute({
	children,
	redirectTo = "/",
}: PublicOnlyRouteProps) {
	const { accessToken } = useStore(authStore);

	if (accessToken) {
		return <Navigate to={redirectTo} />;
	}

	return <>{children}</>;
}
