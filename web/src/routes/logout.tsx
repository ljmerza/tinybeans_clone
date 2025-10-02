import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useRef } from "react";
import { useLogout } from "@/modules/login/hooks";

function LogoutPage() {
	const logout = useLogout();
	const navigate = useNavigate();
	const hasLoggedOut = useRef(false);

	useEffect(() => {
		if (hasLoggedOut.current) return;
		hasLoggedOut.current = true;

		const doLogout = async () => {
			await logout.mutateAsync();
			navigate({ to: "/" });
		};
		doLogout();
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, []);

	return (
		<div className="mx-auto max-w-sm p-6">
			<div className="text-center">
				<p className="text-lg">Logging out...</p>
			</div>
		</div>
	);
}

export const Route = createFileRoute("/logout")({
	component: LogoutPage,
});
