import type { ApiError } from "@/types";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { StatusMessage } from "@/components";
import { LoadingState } from "@/components/LoadingState";
import { Button } from "@/components/ui/button";
import { rememberInviteRedirect } from "@/features/circles/utils/inviteAnalytics";
import { useApiMessages } from "@/i18n";
import { useNavigate } from "@tanstack/react-router";

import { useMagicLoginVerify } from "../hooks/authHooks";

type MagicLoginHandlerProps = {
	token?: string;
	redirect?: string;
};

export function MagicLoginHandler({ token, redirect }: MagicLoginHandlerProps) {
	const { t } = useTranslation();
	const navigate = useNavigate();
	const magicLoginVerify = useMagicLoginVerify({ redirect });
	const { getGeneral } = useApiMessages();
	const [status, setStatus] = useState<"verifying" | "success" | "error">(
		"verifying",
	);
	const [errorMessage, setErrorMessage] = useState<string>("");

	useEffect(() => {
		if (redirect) {
			rememberInviteRedirect(redirect);
		}
	}, [redirect]);

	useEffect(() => {
		if (!token) {
			setStatus("error");
			setErrorMessage(t("errors.magic_link_invalid"));
			return;
		}

		magicLoginVerify
			.mutateAsync({ token })
			.then(() => {
				setStatus("success");
				// Navigation handled by hook
			})
			.catch((error) => {
				const apiError = error as ApiError;
				setStatus("error");

				// Extract error message
				const generals = getGeneral(apiError.messages);
				if (generals.length > 0) {
					setErrorMessage(generals[0]);
				} else {
					setErrorMessage(t("errors.magic_link_invalid"));
				}
			});
	}, [token, magicLoginVerify, getGeneral, t]);

	if (status === "verifying") {
		return (
			<div className="mx-auto max-w-sm p-6 space-y-4">
				<LoadingState
					layout="section"
					className="py-8"
					message={t("auth.magic_link.verifying")}
				/>
			</div>
		);
	}

	if (status === "success") {
		return (
			<div className="mx-auto max-w-sm p-6 space-y-4">
				<StatusMessage variant="success">
					{t("auth.magic_link.success")}
				</StatusMessage>
			</div>
		);
	}

	return (
		<div className="mx-auto max-w-sm p-6 space-y-4">
			<StatusMessage variant="error">{errorMessage}</StatusMessage>
			<Button
				onClick={() =>
					navigate({
						to: "/login",
						search: redirect ? { redirect } : undefined,
					})
				}
				className="w-full"
			>
				{t("auth.password_reset.back_to_login")}
			</Button>
		</div>
	);
}
