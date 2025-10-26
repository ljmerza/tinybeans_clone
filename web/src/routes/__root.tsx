import { ErrorBoundary } from "@/components/ErrorBoundary";
import { useAuthSession } from "@/features/auth";
import { loadInvitation } from "@/features/circles/utils/invitationStorage";
import { Outlet, createRootRoute, useNavigate, useRouterState } from "@tanstack/react-router";
import { useEffect } from "react";
import { TanStackRouterDevtools } from "@tanstack/react-router-devtools";

const isDevelopment = import.meta.env.DEV;


function EmailVerificationRedirect() {
	const session = useAuthSession();
	const navigate = useNavigate();
	const routerState = useRouterState();

	useEffect(() => {
		if (!session.isReady || !session.isAuthenticated) {
			return;
		}

		const pathname = routerState.location.pathname;
		const allowedPaths = [
			"/verify-email",
			"/verify-email-required",
			"/logout",
			"/auth/google-callback",
			"/invitations/accept", // Allow invite acceptance for unverified users (email auto-verified on finalize)
		];

		if (!session.user?.email_verified) {
			// Don't redirect if there's a pending invitation (email will be auto-verified during finalization)
			const pendingInvitation = loadInvitation();
			if (pendingInvitation) {
				return;
			}

			const isAllowed = allowedPaths.some((path) => pathname.startsWith(path));
			if (!isAllowed) {
				void navigate({ to: "/verify-email-required", replace: true });
			}
			return;
		}

		if (pathname.startsWith("/verify-email-required")) {
			const destination = session.user?.needs_circle_onboarding
				? "/circles/onboarding"
				: "/";
			void navigate({
				to: destination === "/circles/onboarding" ? "/circles/onboarding" : "/",
				replace: true,
			});
		}
	}, [
		session.isAuthenticated,
		session.isReady,
		session.user?.email_verified,
		session.user?.needs_circle_onboarding,
		navigate,
		routerState.location.pathname,
	]);

	return null;
}

function RootComponent() {
	return (
		<ErrorBoundary>
			<EmailVerificationRedirect />
			<Outlet />
			{isDevelopment && <TanStackRouterDevtools />}
		</ErrorBoundary>
	);
}

export const Route = createRootRoute({
	component: RootComponent,
});
