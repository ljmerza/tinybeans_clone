import { Layout } from "@/components/Layout";
import { Button } from "@/components/ui/button";
import {
	getOAuthState,
	useGoogleOAuth,
	validateOAuthState,
} from "@/features/auth";
import { useNavigate, useSearch } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

export default function GoogleCallbackPage() {
	const navigate = useNavigate();
	const searchParams = useSearch({ from: "/auth/google-callback" as const });
	const { handleCallback, error } = useGoogleOAuth();
	const [hasProcessed, setHasProcessed] = useState(false);
	const [clientError, setClientError] = useState<string | null>(null);
	const { t } = useTranslation();

	useEffect(() => {
		if (hasProcessed) return;

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

		setHasProcessed(true);
		handleCallback(searchParams.code, searchParams.state);
	}, [searchParams, handleCallback, navigate, hasProcessed, t]);

	if (error || clientError) {
		return (
			<Layout.Error
				showHeader={false}
				title={t("auth.oauth.callback_error_title", { defaultValue: "Sign-in failed" })}
				message={clientError || t("auth.oauth.callback_error_description", { defaultValue: "An error occurred during sign-in. Please try again." })}
				actionLabel={t("common.back_to_login", { defaultValue: "← Back to login" })}
				onAction={() => navigate({ to: "/login" })}
			/>
		);
	}

	return (
		<Layout.Loading
			showHeader={false}
			message={t("auth.oauth.processing", { defaultValue: "Processing Google sign-in..." })}
			description={t("auth.oauth.processing_description", { defaultValue: "Please wait while we verify your account." })}
		/>
	);
}
