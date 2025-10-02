import { LoadingPage } from "@/components/LoadingSpinner";
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

		const doLogout = async () => {
			try {
				await logout.mutateAsync();
				navigate({ to: "/" });
			} catch (error) {
				console.error("Logout error:", error);
				// Navigate to home even if logout fails
				navigate({ to: "/" });
			}
		};
		doLogout();
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, []);

	return <LoadingPage message="Logging out..." />;
}

export const Route = createFileRoute("/logout")({
	component: LogoutPage,
});
