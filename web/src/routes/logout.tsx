import { LoadingPage } from "@/components/LoadingPage";
import { useLogout } from "@/modules/login/hooks";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useRef } from "react";

function LogoutPage() {
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

	return <LoadingPage message="Logging out..." />;
}

export const Route = createFileRoute("/logout")({
	component: LogoutPage,
});
