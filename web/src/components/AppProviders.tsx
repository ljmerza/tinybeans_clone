/**
 * App Providers
 * Encapsulates all context providers in a single component
 */

import { AuthSessionProvider } from "@/features/auth/context/AuthSessionProvider";
import { ThemeProvider } from "@/features/theme";
import { router } from "@/router";
import { type QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "@tanstack/react-router";
import type { ReactNode } from "react";
import { Toaster } from "sonner";


interface AppProvidersProps {
	children?: ReactNode;
	queryClient: QueryClient;
	isInitializing?: boolean;
}

/**
 * Wraps the application with all necessary providers
 */
export function AppProviders({
	queryClient,
	isInitializing = false,
}: AppProvidersProps) {
	return (
		<ThemeProvider>
			<QueryClientProvider client={queryClient}>
				<AuthSessionProvider isInitializing={isInitializing}>
					<RouterProvider router={router} context={{ queryClient }} />
					<Toaster
						richColors
						position="top-right"
						duration={3000}
						closeButton
						containerAriaLabel="Notifications"
					/>
				</AuthSessionProvider>
			</QueryClientProvider>
		</ThemeProvider>
	);
}
