/**
 * App Providers
 * Encapsulates all context providers in a single component
 */

import { AuthSessionProvider } from "@/features/auth/context/AuthSessionProvider";
import { type QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider, createRouter } from "@tanstack/react-router";
import type { ReactNode } from "react";
import { Toaster } from "sonner";

// Import the generated route tree
import { routeTree } from "../routeTree.gen";

interface AppProvidersProps {
	children?: ReactNode;
	queryClient: QueryClient;
	isInitializing?: boolean;
}

const router = createRouter({
	routeTree,
	defaultPreload: "intent",
	scrollRestoration: true,
	defaultStructuralSharing: true,
	defaultPreloadStaleTime: 0,
});

// Register router type
declare module "@tanstack/react-router" {
	interface Register {
		router: typeof router;
	}
}

/**
 * Wraps the application with all necessary providers
 */
export function AppProviders({
	queryClient,
	isInitializing = false,
}: AppProvidersProps) {
	return (
		<QueryClientProvider client={queryClient}>
			<AuthSessionProvider isInitializing={isInitializing}>
				<RouterProvider router={router} context={{ queryClient }} />
				<Toaster richColors position="top-right" duration={3000} closeButton />
			</AuthSessionProvider>
		</QueryClientProvider>
	);
}

export { router };
