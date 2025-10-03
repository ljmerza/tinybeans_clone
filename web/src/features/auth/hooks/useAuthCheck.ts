import { useNavigate } from "@tanstack/react-router";
import { useStore } from "@tanstack/react-store";
import { useCallback } from "react";
import { authStore } from "../store/authStore";

/**
 * Custom hook to check authentication status and navigate
 */
export function useAuthCheck() {
	const { accessToken } = useStore(authStore);
	const navigate = useNavigate();

	const requireAuth = useCallback(() => {
		if (!accessToken) {
			navigate({ to: "/login" });
			return false;
		}
		return true;
	}, [accessToken, navigate]);

	const requireNoAuth = useCallback(() => {
		if (accessToken) {
			navigate({ to: "/" });
			return false;
		}
		return true;
	}, [accessToken, navigate]);

	return {
		isAuthenticated: !!accessToken,
		requireAuth,
		requireNoAuth,
	};
}
