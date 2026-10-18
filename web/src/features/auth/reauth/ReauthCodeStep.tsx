import { StatusMessage } from "@/components";
import { Button } from "@/components/ui/button";
import { VerificationInput } from "@/features/twofa/components/VerificationInput";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { apiErrorMessage } from "./errors";
import { useSendReauthCode } from "./useSendReauthCode";

/** Length of the emailed code. */
export const REAUTH_CODE_LENGTH = 6;

export interface ReauthCodeStepProps {
	value: string;
	onChange: (code: string) => void;
	/** Called once all digits are in, e.g. to submit straight away. */
	onComplete?: (code: string) => void;
	disabled?: boolean;
	/** Why the last code was refused, from the protected request. */
	error?: string;
}

/**
 * Re-authentication for a sensitive action: emails the user a one-time code
 * when it mounts and takes it in a 6-digit input, with a Resend link. The
 * parent sends the code along with its own request, which checks it. It never
 * says where the code went, like the API.
 */
export function ReauthCodeStep({
	value,
	onChange,
	onComplete,
	disabled = false,
	error,
}: ReauthCodeStepProps) {
	const { t } = useTranslation();
	const send = useSendReauthCode();
	const [resent, setResent] = useState(false);
	const sentOnMount = useRef(false);
	const { mutate } = send;

	useEffect(() => {
		// Once per mount, even when StrictMode runs effects twice.
		if (sentOnMount.current) return;
		sentOnMount.current = true;
		mutate();
	}, [mutate]);

	const resend = () => {
		setResent(true);
		onChange("");
		send.mutate();
	};

	let status: string;
	if (send.isPending) {
		status = t("auth.reauth.sending");
	} else if (send.isError) {
		status = "";
	} else if (resent) {
		status = t("auth.reauth.resent");
	} else {
		status = t("auth.reauth.sent");
	}

	return (
		<div className="space-y-4">
			<div className="space-y-1">
				<h3 className="text-sm font-medium leading-none">
					{t("auth.reauth.title")}
				</h3>
				{status && <p className="text-sm text-muted-foreground">{status}</p>}
				{send.isError && (
					<StatusMessage variant="error">
						{apiErrorMessage(send.error, t, "auth.reauth.send_failed")}
					</StatusMessage>
				)}
			</div>
			<VerificationInput
				length={REAUTH_CODE_LENGTH}
				value={value}
				onChange={onChange}
				onComplete={onComplete}
				disabled={disabled}
			/>
			{error && (
				<StatusMessage variant="error" align="center">
					{error}
				</StatusMessage>
			)}
			<div className="text-center">
				<Button
					type="button"
					variant="link"
					size="sm"
					disabled={send.isPending || disabled}
					onClick={resend}
				>
					{t("auth.reauth.resend")}
				</Button>
			</div>
		</div>
	);
}
