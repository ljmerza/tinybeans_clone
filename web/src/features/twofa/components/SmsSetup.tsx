import { Wizard, WizardStep } from "@/components";
import { extractApiError } from "@/features/auth/utils";
import { showToast } from "@/lib/toast";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useInitialize2FASetup, useVerify2FASetup } from "../hooks";
import { SmsIntroStep } from "./setup/sms/SmsIntroStep";
import { SmsRecoveryStep } from "./setup/sms/SmsRecoveryStep";
import { SmsVerifyStep } from "./setup/sms/SmsVerifyStep";

type SetupStep = "intro" | "verify" | "recovery";

interface SmsSetupProps {
	defaultPhone?: string;
	onComplete?: () => void;
	onCancel?: () => void;
}

export function SmsSetup({
	defaultPhone = "",
	onComplete,
	onCancel,
}: SmsSetupProps) {
	const [step, setStep] = useState<SetupStep>("intro");
	const [phone, setPhone] = useState(defaultPhone);
	const [code, setCode] = useState("");
 	const { t } = useTranslation();

	const initSetup = useInitialize2FASetup();
	const verifySetup = useVerify2FASetup();

	const recoveryCodes = verifySetup.data?.recovery_codes;
	const latestMessage =
		initSetup.data?.message ?? t("twofa.setup.sms.message");

	return (
		<Wizard currentStep={step}>
			<WizardStep step="intro">
				<SmsIntroStep
					phone={phone}
					onPhoneChange={setPhone}
					isSending={initSetup.isPending}
					errorMessage={initSetup.error?.message}
					onSend={async () => {
						try {
							await initSetup.mutateAsync({
								method: "sms",
								phone_number: phone.trim(),
							});
							setStep("verify");
						} catch (error) {
						const message = extractApiError(
							error,
							t("twofa.errors.sms_send"),
						);
							showToast({ message, level: "error" });
						}
					}}
					onCancel={onCancel}
				/>
			</WizardStep>

			<WizardStep step="verify">
				<SmsVerifyStep
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
							t("twofa.errors.sms_verify"),
						);
							showToast({ message, level: "error" });
							setCode("");
						}
					}}
					onResend={async () => {
						try {
							await initSetup.mutateAsync({
								method: "sms",
								phone_number: phone.trim(),
							});
							// Invalidate old code locally
							setCode("");
							verifySetup.reset();
						} catch (error) {
						const message = extractApiError(
							error,
							t("twofa.errors.sms_resend"),
						);
							showToast({ message, level: "error" });
						}
					}}
					onCancel={onCancel}
				/>
			</WizardStep>

			<WizardStep step="recovery">
				<SmsRecoveryStep
					recoveryCodes={recoveryCodes}
					onComplete={onComplete ?? (() => undefined)}
				/>
			</WizardStep>
		</Wizard>
	);
}
