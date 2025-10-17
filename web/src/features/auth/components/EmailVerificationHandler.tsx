import { StatusMessage } from "@/components";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { Button } from "@/components/ui/button";
import { useApiMessages } from "@/i18n";
import type { ApiResponseWithMessages } from "@/types";
import { useNavigate } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import type { HttpError } from "@/lib/httpClient";
import { apiClient } from "../api/authClient";

type EmailVerificationHandlerProps = {
	token?: string;
};

type VerificationStatus = "verifying" | "success" | "error";

export function EmailVerificationHandler({ token }: EmailVerificationHandlerProps) {
	const { t } = useTranslation();
	const navigate = useNavigate();
	const { getGeneral } = useApiMessages();
	const [status, setStatus] = useState<VerificationStatus>("verifying");
	const [message, setMessage] = useState<string>("");
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
			setMessage(t("auth.email_verification.invalid_link"));
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

		void apiClient
			.post<ApiResponseWithMessages>("/auth/verify-email/confirm/", { token })
			.then((response) => {
				if (!isMountedRef.current || latestTokenRef.current !== token) {
					return;
				}
				const generalMessages = getGeneralRef.current(response.messages);
				setMessage(
					generalMessages[0] ??
					tRef.current("auth.email_verification.success"),
				);
				setStatus("success");
			})
			.catch((error: unknown) => {
				if (!isMountedRef.current || latestTokenRef.current !== token) {
					return;
				}
				const httpError = error as HttpError;
				const generalMessages = getGeneralRef.current(httpError.messages);
				setMessage(
					generalMessages[0] ??
					tRef.current("auth.email_verification.error"),
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
				<>
					<StatusMessage variant="info" align="center">
						{t("auth.email_verification.verifying")}
					</StatusMessage>
					<div className="flex justify-center">
						<LoadingSpinner />
					</div>
				</>
			) : (
				<>
					<StatusMessage
						variant={status === "success" ? "success" : "error"}
						align="center"
					>
						{message}
					</StatusMessage>
					<Button
						className="w-full"
						onClick={() => {
							// Attempt to close the current window/tab; fallback to navigation if blocked.
							const closed = window.close();
							if (!closed) {
								navigate({ to: status === "success" ? "/" : "/login" });
							}
						}}
					>
						{status === "success"
							? t("auth.email_verification.close_tab")
							: t("auth.email_verification.close_tab_error")}
					</Button>
				</>
			)}
		</div>
	);
}
