import { createFileRoute, redirect } from "@tanstack/react-router";

// The circles list lives in settings now; keep old links and bookmarks working.
export const Route = createFileRoute("/circles/")({
	beforeLoad: () => {
		throw redirect({ to: "/profile/circles", replace: true });
	},
});
