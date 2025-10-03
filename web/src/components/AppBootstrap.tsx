/**
 * App Bootstrap
 * Handles async startup logic (CSRF + session hydration) with Suspense
 */

import { refreshAccessToken } from "@/features/auth";
import { ensureCsrfToken } from "@/lib/csrf";
import { type ReactNode, useEffect, useState } from "react";
import { LoadingPage } from "./LoadingPage";
import { StandardError } from "./StandardError";

interface AppBootstrapProps {
	children: ReactNode;
	onInitialized?: () => void;
}

/**
 * Bootstrap component that initializes CSRF and session before rendering app
 */
export function AppBootstrap({ children, onInitialized }: AppBootstrapProps) {
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
				await refreshAccessToken();

				if (mounted) {
					setStatus("ready");
					onInitialized?.();
				}
			} catch (err) {
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

		bootstrap();

		return () => {
			mounted = false;
		};
	}, [onInitialized]);

	if (status === "loading") {
		return <LoadingPage message="Initializing..." />;
	}

	if (status === "error") {
		return (
			<StandardError
				title="Initialization Error"
				message={error?.message ?? "Failed to start application"}
				description="Please refresh the page to try again"
				actionLabel="Refresh"
				onAction={() => window.location.reload()}
			/>
		);
	}

	return <>{children}</>;
}
