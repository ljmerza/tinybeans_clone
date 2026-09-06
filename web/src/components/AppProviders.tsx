/**
 * App Providers
 * Encapsulates all context providers in a single component
 */

import { AuthSessionProvider } from "@/features/auth/context/AuthSessionProvider";
import { ThemeProvider } from "@/features/theme";
import { createQueryPersistOptions } from "@/lib/query/persister";
import { router } from "@/router";
import { type QueryClient, useIsRestoring } from "@tanstack/react-query";
import { PersistQueryClientProvider } from "@tanstack/react-query-persist-client";
import { RouterProvider } from "@tanstack/react-router";
import type { ReactNode } from "react";
import { Toaster } from "sonner";

const persistOptions = createQueryPersistOptions();

/**
 * Holds rendering until the persisted query cache is restored from
 * localStorage so route loaders see cached data instead of racing it.
 * Restoring from sync storage resolves within a microtask.
 */
function WaitForCacheRestore({ children }: { children: ReactNode }) {
	const isRestoring = useIsRestoring();
	if (isRestoring) {
		return null;
	}
	return <>{children}</>;
}

interface AppProvidersProps {
	children?: ReactNode;
	queryClient: QueryClient;
	isInitializing?: boolean;
}

/**
 * Wraps the application with all necessary providers
 */
export function AppProviders({
	children,
	queryClient,
	isInitializing = false,
}: AppProvidersProps) {
	return (
		<ThemeProvider>
			<PersistQueryClientProvider
				client={queryClient}
				persistOptions={persistOptions}
			>
				<WaitForCacheRestore>
					<AuthSessionProvider isInitializing={isInitializing}>
						{/* While bootstrapping (or on bootstrap error) render the given
						    screen instead of the router: mounting the router early runs
						    route guards before the session is restored, so a refresh on
						    a protected page bounced to /login. */}
						{children ?? (
							<RouterProvider router={router} context={{ queryClient }} />
						)}
						<Toaster
							richColors
							position="top-right"
							duration={3000}
							closeButton
							containerAriaLabel="Notifications"
						/>
					</AuthSessionProvider>
				</WaitForCacheRestore>
			</PersistQueryClientProvider>
		</ThemeProvider>
	);
}
