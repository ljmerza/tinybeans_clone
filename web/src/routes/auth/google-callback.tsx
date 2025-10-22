import { LoadingState } from "@/components/LoadingState";
import { Button } from "@/components/ui/button";
import {
	getOAuthState,
	useGoogleOAuth,
	validateOAuthState,
} from "@/features/auth";
import { rememberInviteRedirect } from "@/features/circles/utils/inviteAnalytics";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { z } from "zod";

// Search params schema for OAuth callback
const searchParamsSchema = z.object({
	code: z.string().optional(),
	state: z.string().optional(),
	error: z.string().optional(),
	error_description: z.string().optional(),
	redirect: z.string().optional(),
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
	const [clientError, setClientError] = useState<string | null>(null);
	const { t } = useTranslation();

	useEffect(() => {
		if (searchParams.redirect) {
			rememberInviteRedirect(searchParams.redirect);
		}

		// Prevent double processing
		if (hasProcessed) return;

		// Check for Google OAuth error
		if (searchParams.error) {
			const errorMsg = searchParams.error_description || searchParams.error;
			if (errorMsg === "access_denied") {
				setClientError(
					t("errors.oauth.google_cancelled", {
						defaultValue: "You cancelled the Google sign-in process.",
					}),
				);
			} else {
				setClientError(errorMsg);
			}
			setHasProcessed(true);
			setTimeout(() => navigate({ to: "/login" }), 2000);
			return;
		}

		// Validate required parameters
		if (!searchParams.code || !searchParams.state) {
			setClientError(
				t("errors.oauth.invalid_callback", {
					defaultValue: "Missing required OAuth parameters. Please try again.",
				}),
			);
			setHasProcessed(true);
			setTimeout(() => navigate({ to: "/login" }), 2000);
			return;
		}

		// Validate state token (CSRF protection)
		const storedState = getOAuthState();
		if (!validateOAuthState(searchParams.state, storedState)) {
			setClientError(
				t("errors.oauth.state_mismatch", {
					defaultValue:
						"Security validation failed. Please try signing in again.",
				}),
			);
			setHasProcessed(true);
			setTimeout(() => navigate({ to: "/login" }), 2000);
			return;
		}

		// Process the callback
		setHasProcessed(true);
		handleCallback(searchParams.code, searchParams.state);
	}, [searchParams, handleCallback, navigate, hasProcessed, t]);

	// Show error state
	if (error || clientError) {
		return (
			<Layout.Error
				showHeader={false}
				title={t("auth.oauth.callback_error_title", {
					defaultValue: "Sign-in failed",
				})}
				message={
					clientError ||
					t("auth.oauth.callback_error_description", {
						defaultValue: "An error occurred during sign-in. Please try again.",
					})
				}
				description={t("auth.oauth.callback_error_help", {
					defaultValue:
						"You will be redirected shortly or use the button below.",
				})}
				actionLabel={t("common.back_to_login", {
					defaultValue: "← Back to login",
				})}
				onAction={() => navigate({ to: "/login" })}
				icon={
					<svg
						className="h-10 w-10 text-destructive"
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
				}
			/>
		);
	}

	// Show loading state
	return (
		<Layout.Loading
			showHeader={false}
			message={t("auth.oauth.processing", {
				defaultValue: "Processing Google sign-in...",
			})}
			description={t("auth.oauth.processing_description", {
				defaultValue: "Please wait while we verify your account.",
			})}
			icon={
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
			}
		/>
	);
}
