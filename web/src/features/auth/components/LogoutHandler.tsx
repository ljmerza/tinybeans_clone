import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";

import { LoadingState } from "@/components/LoadingState";
import { useNavigate } from "@tanstack/react-router";

import { useLogout } from "../hooks/authHooks";

export function LogoutHandler() {
	const { t } = useTranslation();
	const logout = useLogout();
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

	return (
		<LoadingState
			layout="fullscreen"
			message={t("auth.logout.logging_out")}
		/>
	);
}
