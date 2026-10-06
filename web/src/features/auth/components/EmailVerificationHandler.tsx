import { LoadingSpinner, StatusMessage } from "@/components";
import { IconTile } from "@/components/IconTile";
import { Button } from "@/components/ui/button";
import { useAuthSession, setAccessToken } from "@/features/auth";
import { useApiMessages } from "@/i18n";
import { showToast } from "@/lib/toast";
import { useNavigate } from "@tanstack/react-router";
import { Mail, MailCheck, MailX } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import type { HttpError } from "@/lib/httpClient";
import type { EmailVerificationConfirmResponse } from "../types";
import { authServices } from "../api/services";
import { SecureBrandPanel } from "./AuthBrandPanel";
import { AuthSplitLayout } from "./AuthSplitLayout";

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

	// biome-ignore lint/correctness/useExhaustiveDependencies: must run once per token; adding navigate/session would re-trigger verification
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

	const statusIcon =
		status === "verifying" ? (
			<IconTile icon={Mail} tone="amber" size="lg" />
		) : status === "success" ? (
			<IconTile icon={MailCheck} tone="sky" size="lg" />
		) : (
			<IconTile icon={MailX} tone="rose" size="lg" />
		);

	return (
		<AuthSplitLayout
			aside={<SecureBrandPanel />}
			icon={statusIcon}
			title={t("auth.email_verification.title")}
		>
			{status === "verifying" ? (
				<div
					className="flex items-center gap-3 text-muted-foreground"
					aria-live="polite"
					aria-busy
				>
					<LoadingSpinner size="sm" className="text-primary" />
					{t("auth.email_verification.verifying")}
				</div>
			) : status === "success" ? (
				<StatusMessage variant="success">{message}</StatusMessage>
			) : (
				<div className="space-y-4">
					<StatusMessage variant="error">{message}</StatusMessage>
					<Button
						variant="outline"
						onClick={() => {
							window.close();
							navigate({ to: "/login" });
						}}
					>
						{t("auth.email_verification.close_tab_error")}
					</Button>
				</div>
			)}
		</AuthSplitLayout>
	);
}
