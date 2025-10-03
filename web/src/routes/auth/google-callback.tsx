import { LoadingSpinner } from "@/components/LoadingSpinner";
import { Button } from "@/components/ui/button";
import { useGoogleOAuth } from "@/modules/oauth/hooks";
import { getOAuthErrorMessage, getOAuthState, validateOAuthState } from "@/modules/oauth/utils";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { z } from "zod";

// Search params schema for OAuth callback
const searchParamsSchema = z.object({
	code: z.string().optional(),
	state: z.string().optional(),
	error: z.string().optional(),
	error_description: z.string().optional(),
});

export const Route = createFileRoute("/auth/google-callback")({
	validateSearch: searchParamsSchema,
	component: GoogleCallbackPage,
});

function GoogleCallbackPage() {
	const navigate = useNavigate();
	const searchParams = Route.useSearch();
	const { handleCallback, error } = useGoogleOAuth();
	const [hasProcessed, setHasProcessed] = useState(false);

	useEffect(() => {
		// Prevent double processing
		if (hasProcessed) return;

		// Check for Google OAuth error
		if (searchParams.error) {
			const errorMsg = searchParams.error_description || searchParams.error;
			toast.error("Google Sign-in Cancelled", {
				description: errorMsg === "access_denied" 
					? "You cancelled the Google sign-in process."
					: errorMsg,
			})
			setHasProcessed(true);
			setTimeout(() => navigate({ to: "/login" }), 2000);
			return
		}

		// Validate required parameters
		if (!searchParams.code || !searchParams.state) {
			toast.error("Invalid OAuth Callback", {
				description: "Missing required OAuth parameters. Please try again.",
			})
			setHasProcessed(true);
			setTimeout(() => navigate({ to: "/login" }), 2000);
			return
		}

		// Validate state token (CSRF protection)
		const storedState = getOAuthState();
		if (!validateOAuthState(searchParams.state, storedState)) {
			toast.error("OAuth State Mismatch", {
				description: "Security validation failed. Please try signing in again.",
			})
			setHasProcessed(true);
			setTimeout(() => navigate({ to: "/login" }), 2000);
			return
		}

		// Process the callback
		setHasProcessed(true);
		handleCallback(searchParams.code, searchParams.state);
	}, [searchParams, handleCallback, navigate, hasProcessed]);

	// Show error state
	if (error) {
		const errorInfo = getOAuthErrorMessage(error);
		return (
			<div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
				<div className="max-w-md w-full space-y-6 text-center">
					<div className="bg-white p-8 rounded-lg shadow-lg">
						{/* Error Icon */}
						<div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100 mb-4">
							<svg
								className="h-6 w-6 text-red-600"
								fill="none"
								viewBox="0 0 24 24"
								stroke="currentColor"
							>
								<title>Error</title>
								<path
									strokeLinecap="round"
									strokeLinejoin="round"
									strokeWidth={2}
									d="M6 18L18 6M6 6l12 12"
								/>
							</svg>
						</div>

						{/* Error Title */}
						<h2 className="text-2xl font-bold text-gray-900 mb-2">
							{errorInfo.title}
						</h2>

						{/* Error Message */}
						<p className="text-gray-600 mb-6">{errorInfo.message}</p>

						{/* Action Buttons */}
						<div className="space-y-3">
							<Button
								onClick={() => navigate({ to: "/login" })}
								className="w-full"
							>
								Back to Login
							</Button>
							{errorInfo.action && errorInfo.action === "Retry" && (
								<Button
									variant="outline"
									onClick={() => window.location.reload()}
									className="w-full"
								>
									Try Again
								</Button>
							)}
						</div>
					</div>
				</div>
			</div>
		)
	}

	// Show loading state
	return (
		<div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
			<div className="max-w-md w-full space-y-6 text-center">
				<div className="bg-white p-8 rounded-lg shadow-lg">
					{/* Google Logo */}
					<div className="mx-auto flex items-center justify-center h-16 w-16 mb-4">
						<svg
							className="w-16 h-16"
							viewBox="0 0 24 24"
							xmlns="http://www.w3.org/2000/svg"
						>
							<title>Google Logo</title>
							<path
								d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
								fill="#4285F4"
							/>
							<path
								d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
								fill="#34A853"
							/>
							<path
								d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
								fill="#FBBC05"
							/>
							<path
								d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
								fill="#EA4335"
							/>
						</svg>
					</div>

					{/* Loading Spinner */}
					<LoadingSpinner />

					{/* Loading Text */}
					<h2 className="text-xl font-semibold text-gray-900 mt-4 mb-2">
						Completing sign-in with Google...
					</h2>
					<p className="text-gray-600 text-sm">
						Please wait while we verify your account
					</p>
				</div>
			</div>
		</div>
	)
}
