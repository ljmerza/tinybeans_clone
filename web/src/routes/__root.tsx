import { ErrorBoundary } from "@/components/ErrorBoundary";
import { Outlet, createRootRoute } from "@tanstack/react-router";
import { TanStackRouterDevtools } from "@tanstack/react-router-devtools";

const isDevelopment = import.meta.env.DEV;

function RootComponent() {
	return (
		<ErrorBoundary>
			<Outlet />
			{isDevelopment && <TanStackRouterDevtools />}
		</ErrorBoundary>
	);
}

export const Route = createRootRoute({
	component: RootComponent,
});
