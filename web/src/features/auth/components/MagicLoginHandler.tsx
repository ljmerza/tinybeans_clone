import type { ApiError } from "@/types";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { LoadingSpinner, StatusMessage } from "@/components";
import { IconTile } from "@/components/IconTile";
import { Button } from "@/components/ui/button";
import { rememberInviteRedirect } from "@/features/circles/utils/inviteAnalytics";
import { useApiMessages } from "@/i18n";
import { useNavigate } from "@tanstack/react-router";
import { LogIn, MailX } from "lucide-react";

import { useMagicLoginVerify } from "../hooks/authHooks";
import { SecureBrandPanel } from "./AuthBrandPanel";
import { AuthSplitLayout } from "./AuthSplitLayout";

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

	return (
		<AuthSplitLayout
			aside={<SecureBrandPanel />}
			icon={
				status === "error" ? (
					<IconTile icon={MailX} tone="rose" size="lg" />
				) : (
					<IconTile icon={LogIn} tone="sky" size="lg" />
				)
			}
			title={t("auth.magic_link.request_title")}
		>
			{status === "verifying" ? (
				<div
					className="flex items-center gap-3 text-muted-foreground"
					aria-live="polite"
					aria-busy
				>
					<LoadingSpinner size="sm" className="text-primary" />
					{t("auth.magic_link.verifying")}
				</div>
			) : status === "success" ? (
				<StatusMessage variant="success">
					{t("auth.magic_link.success")}
				</StatusMessage>
			) : (
				<div className="space-y-4">
					<StatusMessage variant="error">{errorMessage}</StatusMessage>
					<Button
						variant="outline"
						onClick={() =>
							navigate({
								to: "/login",
								search: redirect ? { redirect } : undefined,
							})
						}
					>
						{t("auth.password_reset.back_to_login")}
					</Button>
				</div>
			)}
		</AuthSplitLayout>
	);
}
