import { useEffect, useState } from "react";

import { StatusMessage } from "@/components";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { Button } from "@/components/ui/button";
import { useApiMessages } from "@/i18n";
import { useNavigate } from "@tanstack/react-router";

import { useMagicLoginVerify } from "../hooks/authHooks";

type MagicLoginHandlerProps = {
	token?: string;
};

export function MagicLoginHandler({ token }: MagicLoginHandlerProps) {
	const navigate = useNavigate();
	const magicLoginVerify = useMagicLoginVerify();
	const { getGeneral, translate } = useApiMessages();
	const [status, setStatus] = useState<"verifying" | "success" | "error">(
		"verifying",
	);
	const [errorMessage, setErrorMessage] = useState<string>("");

	useEffect(() => {
		if (!token) {
			setStatus("error");
			setErrorMessage("Invalid or expired magic login link. Please request a new one.");
			return;
		}

		magicLoginVerify
			.mutateAsync({ token })
			.then((response) => {
				setStatus("success");
				// Navigation handled by hook
			})
			.catch((error: any) => {
				setStatus("error");
				
				// Extract error message
				const generals = getGeneral(error.messages);
				if (generals.length > 0) {
					setErrorMessage(generals[0]);
				} else {
					setErrorMessage("Invalid or expired magic login link. Please request a new one.");
				}
			});
	}, [token, magicLoginVerify, getGeneral]);

	if (status === "verifying") {
		return (
			<div className="mx-auto max-w-sm p-6 space-y-4">
				<StatusMessage variant="info">
					Verifying your magic login link...
				</StatusMessage>
				<div className="flex justify-center">
					<LoadingSpinner />
				</div>
			</div>
		);
	}

	if (status === "success") {
		return (
			<div className="mx-auto max-w-sm p-6 space-y-4">
				<StatusMessage variant="success">
					Successfully logged in! Redirecting...
				</StatusMessage>
			</div>
		);
	}

	return (
		<div className="mx-auto max-w-sm p-6 space-y-4">
			<StatusMessage variant="error">
				{errorMessage}
			</StatusMessage>
			<Button onClick={() => navigate({ to: "/login" })} className="w-full">
				Return to Login
			</Button>
		</div>
	);
}
