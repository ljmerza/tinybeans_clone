import { StatusMessage } from "@/components";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { Button } from "@/components/ui/button";
import { useApiMessages } from "@/i18n";
import type { ApiError } from "@/types";
import { useNavigate } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { useVerifyEmailConfirm } from "../hooks/emailVerificationHooks";

type EmailVerificationHandlerProps = {
	token?: string;
};

type VerificationStatus = "verifying" | "success" | "error";

export function EmailVerificationHandler({ token }: EmailVerificationHandlerProps) {
	const { t } = useTranslation();
	const navigate = useNavigate();
	const { getGeneral } = useApiMessages();
	const verifyEmail = useVerifyEmailConfirm();
	const [status, setStatus] = useState<VerificationStatus>("verifying");
	const [message, setMessage] = useState<string>("");
	const attemptedTokenRef = useRef<string | undefined>(undefined);
	const getGeneralRef = useRef(getGeneral);
	const verifyEmailRef = useRef(verifyEmail);

	getGeneralRef.current = getGeneral;
	verifyEmailRef.current = verifyEmail;

	useEffect(() => {
		if (!token) {
			setStatus("error");
			setMessage(t("auth.email_verification.invalid_link"));
			attemptedTokenRef.current = undefined;
			return;
		}

		if (attemptedTokenRef.current === token) {
			return;
		}
		attemptedTokenRef.current = token;

		let isActive = true;

		verifyEmailRef.current
			.mutateAsync({ token })
			.then((response) => {
				if (!isActive) return;
				const generalMessages = getGeneralRef.current(response.messages);
				setMessage(generalMessages[0] ?? t("auth.email_verification.success"));
				setStatus("success");
			})
			.catch((error) => {
				if (!isActive) return;
				const apiError = error as ApiError;
				const generalMessages = getGeneralRef.current(apiError.messages);
				setMessage(
					generalMessages[0] ?? t("auth.email_verification.error"),
				);
				setStatus("error");
			});
		return () => {
			isActive = false;
		};
	}, [token, t]);

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
						onClick={() => navigate({ to: status === "success" ? "/" : "/login" })}
					>
						{status === "success"
							? t("common.back_home")
							: t("common.back_to_login")}
					</Button>
				</>
			)}
		</div>
	);
}
