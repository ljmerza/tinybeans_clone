import { useEffect, useRef } from "react";

import { LoadingPage } from "@/components/LoadingPage";
import { useNavigate } from "@tanstack/react-router";

import { useLogoutModern } from "../hooks/modernHooks";

export function LogoutHandler() {
	const logout = useLogoutModern();
	const navigate = useNavigate();
	const hasLoggedOut = useRef(false);

	useEffect(() => {
		if (hasLoggedOut.current) return;
		hasLoggedOut.current = true;

		void logout
			.mutateAsync()
			.catch((error) => {
				console.error("Logout error:", error);
			})
			.finally(() => {
				navigate({ to: "/" });
			});
	}, [logout, navigate]);

	return <LoadingPage message="Logging out..." />;
}
