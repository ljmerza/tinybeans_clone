import { Wizard, WizardStep } from "@/components";
import { extractApiError } from "@/features/auth/utils";
import { showToast } from "@/lib/toast";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useInitialize2FASetup, useVerify2FASetup } from "../hooks";
import { EmailIntroStep } from "./setup/email/EmailIntroStep";
import { EmailRecoveryStep } from "./setup/email/EmailRecoveryStep";
import { EmailVerifyStep } from "./setup/email/EmailVerifyStep";

type SetupStep = "intro" | "verify" | "recovery";

interface EmailSetupProps {
	onComplete?: () => void;
	onCancel?: () => void;
}

export function EmailSetup({ onComplete, onCancel }: EmailSetupProps) {
	const [step, setStep] = useState<SetupStep>("intro");
	const [code, setCode] = useState("");
 	const { t } = useTranslation();

	const initSetup = useInitialize2FASetup();
	const verifySetup = useVerify2FASetup();

	const recoveryCodes = verifySetup.data?.recovery_codes;
	const latestMessage =
		initSetup.data?.message ?? t("twofa.setup.email.message");

	return (
		<Wizard currentStep={step}>
			<WizardStep step="intro">
				<EmailIntroStep
					isSending={initSetup.isPending}
					errorMessage={initSetup.error?.message}
					onSend={async () => {
						try {
							await initSetup.mutateAsync({ method: "email" });
							setStep("verify");
						} catch (error) {
						const message = extractApiError(
							error,
							t("twofa.errors.email_send"),
						);
							showToast({ message, level: "error" });
						}
					}}
					onCancel={onCancel}
				/>
			</WizardStep>

			<WizardStep step="verify">
				<EmailVerifyStep
					code={code}
					message={latestMessage}
					isVerifying={verifySetup.isPending}
					isResending={initSetup.isPending}
					errorMessage={verifySetup.error?.message}
					onCodeChange={setCode}
					onVerify={async (val) => {
						try {
							await verifySetup.mutateAsync(val ?? code);
							setStep("recovery");
						} catch (error) {
						const message = extractApiError(
							error,
							t("twofa.errors.email_verify"),
						);
							showToast({ message, level: "error" });
							setCode("");
						}
					}}
					onResend={async () => {
						try {
							await initSetup.mutateAsync({ method: "email" });
							// Invalidate old code locally
							setCode("");
							verifySetup.reset();
						} catch (error) {
						const message = extractApiError(
							error,
							t("twofa.errors.email_resend"),
						);
							showToast({ message, level: "error" });
						}
					}}
					onCancel={onCancel}
				/>
			</WizardStep>

			<WizardStep step="recovery">
				<EmailRecoveryStep
					recoveryCodes={recoveryCodes}
					onComplete={onComplete ?? (() => undefined)}
				/>
			</WizardStep>
		</Wizard>
	);
}
