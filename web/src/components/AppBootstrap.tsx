/**
 * App Bootstrap
 * Handles async startup logic (CSRF + session hydration) with Suspense
 */

import { authKeys, authServices, refreshAccessToken } from "@/features/auth";
import type { MeResponse } from "@/features/auth";
import { ensureCsrfToken } from "@/lib/csrf";
import type { HttpError } from "@/lib/httpClient";
import type { QueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { AppProviders } from "./AppProviders";
import { Layout } from "./Layout";

interface AppBootstrapProps {
	queryClient: QueryClient;
}

/**
 * Bootstrap component that initializes CSRF and session before rendering app
 */
export function AppBootstrap({ queryClient }: AppBootstrapProps) {
	const [status, setStatus] = useState<"loading" | "ready" | "error">(
		"loading",
	);
	const [error, setError] = useState<Error | null>(null);

	useEffect(() => {
		let mounted = true;

		async function bootstrap() {
			try {
				// Step 1: Ensure CSRF token is available
				await ensureCsrfToken();

				// Step 2: Try to restore session from refresh token
				const restored = await refreshAccessToken();

				if (restored) {
					try {
						await queryClient.prefetchQuery({
							queryKey: authKeys.session(),
							queryFn: async () => {
								const response = await authServices.getSession({
									suppressErrorToast: true,
								});
								const data = (response.data ?? response) as MeResponse;
								return data.user;
							},
							staleTime: 1000 * 60,
						});
					} catch (sessionErr) {
						const httpError = sessionErr as HttpError | undefined;
						if (httpError?.status !== 401) {
							console.warn(
								"[AppBootstrap] Failed to prefetch auth session:",
								sessionErr,
							);
						}
					}
				}

				if (mounted) {
					setStatus("ready");
				}
			} catch (err) {
				console.error("[AppBootstrap] Bootstrap error:", err);
				if (mounted) {
					setError(
						err instanceof Error
							? err
							: new Error("Failed to initialize application"),
					);
					setStatus("error");
				}
			}
		}

		void bootstrap();

		return () => {
			mounted = false;
		};
	}, [queryClient]);

	if (status === "loading") {
		return <Layout.Loading showHeader={false} layout="fullscreen" message="Initializing..." />;
	}

	if (status === "error") {
		return (
			<Layout.Error
				showHeader={false}
				title="Initialization Error"
				message={error?.message ?? "Failed to start application"}
				actionLabel="Refresh"
				onAction={() => window.location.reload()}
			/>
		);
	}

	return <AppProviders queryClient={queryClient} isInitializing={false} />;
}
