import { Wizard, WizardStep } from "@/components";
import { extractApiError } from "@/features/auth/utils";
import { showToast } from "@/lib/toast";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { combineMessages, useApiMessages } from "@/i18n";
import type { HttpError } from "@/lib/httpClient";
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
	const { showAsToast, getGeneral } = useApiMessages();

	const initSetup = useInitialize2FASetup();
	const verifySetup = useVerify2FASetup();

	const recoveryCodes = verifySetup.data?.recovery_codes;
	const latestMessage = initSetup.data?.message ?? t("twofa.setup.sms.message");

	const resolveErrorMessage = (error: unknown) => {
		const httpError = error as HttpError | undefined;
		if (httpError?.messages?.length) {
			const generalErrors = getGeneral(httpError.messages);
			if (generalErrors.length > 0) {
				return combineMessages(generalErrors);
			}
		}
		return (error as Error | undefined)?.message;
	};

	const introErrorMessage = resolveErrorMessage(initSetup.error);
	const verifyErrorMessage = resolveErrorMessage(verifySetup.error);

	const handleRequestError = (error: unknown, fallbackKey: string) => {
		const httpError = error as HttpError | undefined;
		if (httpError?.messages?.length) {
			showAsToast(httpError.messages, httpError.status ?? 400);
			return;
		}

		const message = extractApiError(error, t(fallbackKey));
		showToast({ message, level: "error" });
	};

	return (
		<Wizard currentStep={step}>
			<WizardStep step="intro">
				<SmsIntroStep
					phone={phone}
					onPhoneChange={setPhone}
					isSending={initSetup.isPending}
					errorMessage={introErrorMessage}
					onSend={async () => {
						try {
							await initSetup.mutateAsync({
								method: "sms",
								phone_number: phone.trim(),
							});
							setStep("verify");
						} catch (error) {
							handleRequestError(error, "twofa.errors.sms_send");
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
					errorMessage={verifyErrorMessage}
					onCodeChange={setCode}
					onVerify={async (val) => {
						try {
							await verifySetup.mutateAsync(val ?? code);
							setStep("recovery");
						} catch (error) {
							handleRequestError(error, "twofa.errors.sms_verify");
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
							handleRequestError(error, "twofa.errors.sms_resend");
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
