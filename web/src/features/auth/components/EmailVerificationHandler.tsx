import { StatusMessage, Layout } from "@/components";
import { Button } from "@/components/ui/button";
import { useAuthSession, setAccessToken } from "@/features/auth";
import { useApiMessages } from "@/i18n";
import { showToast } from "@/lib/toast";
import type { ApiResponseWithMessages } from "@/types";
import { useNavigate } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import type { HttpError } from "@/lib/httpClient";
import type { EmailVerificationConfirmResponse } from "../types";
import { authServices } from "../api/services";

type EmailVerificationHandlerProps = {
	token?: string;
};

type VerificationStatus = "verifying" | "success" | "error";

export function EmailVerificationHandler({
	token,
}: EmailVerificationHandlerProps) {
	const { t } = useTranslation();
	const navigate = useNavigate();
	const { getGeneral } = useApiMessages();
	const [status, setStatus] = useState<VerificationStatus>("verifying");
	const [message, setMessage] = useState<string>("");
	const session = useAuthSession();
	const latestTokenRef = useRef<string | undefined>(undefined);
	const inflightTokenRef = useRef<string | null>(null);
	const getGeneralRef = useRef(getGeneral);
	const tRef = useRef(t);
	const isMountedRef = useRef(false);

	getGeneralRef.current = getGeneral;
	tRef.current = t;

	useEffect(() => {
		isMountedRef.current = true;
		return () => {
			isMountedRef.current = false;
		};
	}, []);

	useEffect(() => {
		if (!token) {
			setStatus("error");
			setMessage(tRef.current("auth.email_verification.invalid_link"));
			latestTokenRef.current = undefined;
			inflightTokenRef.current = null;
			return;
		}

		latestTokenRef.current = token;
		if (inflightTokenRef.current === token) {
			return;
		}
		inflightTokenRef.current = token;
		setStatus("verifying");
		setMessage("");

		void authServices
			.confirmEmailVerification({ token })
			.then(async (response) => {
				if (!isMountedRef.current || latestTokenRef.current !== token) {
					return;
				}
				const generalMessages = getGeneralRef.current(response.messages);
				const payload = (response.data ?? response) as
					| EmailVerificationConfirmResponse
					| undefined;
				setMessage(
					generalMessages[0] ?? tRef.current("auth.email_verification.success"),
				);
				setStatus("success");
				const accessToken = payload?.access_token;
				if (accessToken) {
					setAccessToken(accessToken);
				}
				await session.refetchUser();
				showToast({
					message: tRef.current("auth.email_verification.success_toast"),
					level: "success",
					id: "email-verification-success",
				});
				const redirectTarget = payload?.redirect_url ?? "/circles/onboarding";
				if (redirectTarget === "/circles/onboarding") {
					void navigate({ to: "/circles/onboarding", replace: true });
				} else if (redirectTarget === "/") {
					void navigate({ to: "/", replace: true });
				} else if (typeof window !== "undefined") {
					window.location.assign(redirectTarget);
				}
			})
			.catch((error: unknown) => {
				if (!isMountedRef.current || latestTokenRef.current !== token) {
					return;
				}
				const httpError = error as HttpError;
				const generalMessages = getGeneralRef.current(httpError.messages);
				setMessage(
					generalMessages[0] ?? tRef.current("auth.email_verification.error"),
				);
				setStatus("error");
			})
			.finally(() => {
				if (inflightTokenRef.current === token) {
					inflightTokenRef.current = null;
				}
			});
		// `t` is read via ref to avoid retriggering the effect on language toggles mid-request.
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [token]);

	return (
		<div className="mx-auto max-w-md p-6 space-y-4">
			<h1 className="heading-3 text-center">
				{t("auth.email_verification.title")}
			</h1>

			{status === "verifying" ? (
				<Layout.Loading
					showHeader={false}
					message={t("auth.email_verification.verifying")}
					spinnerSize="md"
				/>
			) : status === "success" ? (
				<StatusMessage variant="success" align="center">{message}</StatusMessage>
			) : (
				<Layout.Error
					showHeader={false}
					message={message}
					actionLabel={t("auth.email_verification.close_tab_error")}
					onAction={() => {
						const closed = window.close();
						if (!closed) {
							navigate({ to: "/login" });
						}
					}}
				/>
			)}
		</div>
	);
}
