import { ErrorBoundary } from "@/components/ErrorBoundary";
import { Outlet, createRootRoute } from "@tanstack/react-router";
import { TanStackRouterDevtools } from "@tanstack/react-router-devtools";

function RootComponent() {
	return (
		<ErrorBoundary>
			<Outlet />
			<TanStackRouterDevtools />
		</ErrorBoundary>
	);
}

export const Route = createRootRoute({
	component: RootComponent,
});
