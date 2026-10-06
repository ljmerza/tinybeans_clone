import { Layout } from "@/components/Layout";
import {
	getAppleOAuthState,
	parseAppleCallbackFragment,
	useAppleOAuth,
	validateOAuthState,
} from "@/features/auth";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

export const Route = createFileRoute("/auth/apple-callback")({
	component: AppleCallbackPage,
});

/** Error codes the API's return view puts in the fragment, besides Apple's own. */
const ERROR_KEYS: Record<string, string> = {
	user_cancelled_authorize: "errors.oauth.apple_cancelled",
	invalid_state: "errors.oauth.invalid_state",
	rate_limited: "errors.rate_limit",
	apple_disabled: "errors.oauth.apple_disabled",
};

function AppleCallbackPage() {
	const navigate = useNavigate();
	const { handleCallback, error } = useAppleOAuth();
	const { t } = useTranslation();
	// Read once: the fragment is stripped from the address bar right after.
	const [params] = useState(() =>
		parseAppleCallbackFragment(window.location.hash),
	);
	const processed = useRef(false);
	const [clientError, setClientError] = useState<string | null>(null);

	useEffect(() => {
		if (processed.current) return;
		processed.current = true;

		if (window.location.hash) {
			window.history.replaceState(
				window.history.state,
				"",
				window.location.pathname,
			);
		}

		const fail = (message: string) => {
			setClientError(message);
			setTimeout(() => navigate({ to: "/login" }), 2000);
		};

		if (params.error) {
			fail(t(ERROR_KEYS[params.error] ?? "errors.oauth.authentication_failed"));
			return;
		}

		if (!params.code || !params.state) {
			fail(t("errors.oauth.invalid_callback"));
			return;
		}

		// CSRF: the state must be the one this browser started with.
		if (!validateOAuthState(params.state, getAppleOAuthState())) {
			fail(t("errors.oauth.state_mismatch"));
			return;
		}

		handleCallback(params.code, params.state);
	}, [params, handleCallback, navigate, t]);

	if (error || clientError) {
		return (
			<Layout.Error
				showHeader={false}
				title={t("auth.oauth.callback_error_title")}
				message={clientError || t("auth.oauth.callback_error_description")}
				description={t("auth.oauth.callback_error_help", {
					defaultValue:
						"You will be redirected shortly or use the button below.",
				})}
				actionLabel={t("common.back_to_login", {
					defaultValue: "← Back to login",
				})}
				onAction={() => navigate({ to: "/login" })}
			/>
		);
	}

	return (
		<Layout.Loading
			showHeader={false}
			message={t("auth.oauth.apple_processing")}
			description={t("auth.oauth.processing_description")}
		/>
	);
}
