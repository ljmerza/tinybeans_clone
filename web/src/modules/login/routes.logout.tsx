import { createRoute, useNavigate } from "@tanstack/react-router";
import type { AnyRoute } from "@tanstack/react-router";
import { useEffect, useRef } from "react";
import { useLogout } from "./hooks";

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

	return (
		<div className="mx-auto max-w-sm p-6">
			<div className="text-center">
				<p className="text-lg">Logging out...</p>
			</div>
		</div>
	);
}

export default (parentRoute: AnyRoute) =>
	createRoute({
		path: "/logout",
		component: LogoutPage,
		getParentRoute: () => parentRoute,
	});
