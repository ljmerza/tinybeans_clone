import { Wizard, WizardStep } from "@/components";
import { extractApiError } from "@/features/auth/utils";
import { showToast } from "@/lib/toast";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useInitialize2FASetup, useVerify2FASetup } from "../hooks";
import type {
	RecoveryCodesResponse,
	TwoFactorSetupResponse,
} from "../types";
import { TotpIntroStep } from "./setup/totp/TotpIntroStep";
import { TotpRecoveryStep } from "./setup/totp/TotpRecoveryStep";
import { TotpScanStep } from "./setup/totp/TotpScanStep";
import { TotpVerifyStep } from "./setup/totp/TotpVerifyStep";

type SetupStep = "intro" | "scan" | "verify" | "recovery";

interface TotpSetupProps {
	onComplete?: () => void;
	onCancel?: () => void;
}

export function TotpSetup({ onComplete, onCancel }: TotpSetupProps) {
	const [step, setStep] = useState<SetupStep>("intro");
	const [code, setCode] = useState("");
	const { t } = useTranslation();

	const initSetup = useInitialize2FASetup();
	const verifySetup = useVerify2FASetup();

	const unwrapApiResponse = <T,>(response: unknown): T | undefined => {
		if (!response || typeof response !== "object") {
			return response as T | undefined;
		}

		if ("data" in response && response.data !== undefined) {
			return (response as { data?: T }).data;
		}

		return response as T;
	};

	const setupData = unwrapApiResponse<TwoFactorSetupResponse>(initSetup.data);
	const recoveryPayload =
		unwrapApiResponse<RecoveryCodesResponse>(verifySetup.data);
	const recoveryCodes = recoveryPayload?.recovery_codes;

	return (
		<Wizard currentStep={step}>
			<WizardStep step="intro">
				<TotpIntroStep
					isInitializing={initSetup.isPending}
					errorMessage={initSetup.error?.message}
					onStart={async () => {
						try {
							await initSetup.mutateAsync({ method: "totp" });
							setStep("scan");
						} catch (error) {
							const message = extractApiError(
								error,
								t("twofa.errors.start_authenticator"),
							);
							showToast({ message, level: "error" });
						}
					}}
					onCancel={onCancel}
				/>
			</WizardStep>

			<WizardStep step="scan">
				<TotpScanStep
					qrCodeImage={setupData?.qr_code_image}
					secret={setupData?.secret}
					onContinue={() => setStep("verify")}
				/>
			</WizardStep>

			<WizardStep step="verify">
				<TotpVerifyStep
					code={code}
					isVerifying={verifySetup.isPending}
					errorMessage={verifySetup.error?.message}
					onCodeChange={setCode}
					onVerify={async (val) => {
						try {
							await verifySetup.mutateAsync(val ?? code);
							setStep("recovery");
						} catch (error) {
							const message = extractApiError(
								error,
								t("twofa.errors.verify_authenticator"),
							);
							showToast({ message, level: "error" });
							setCode("");
						}
					}}
					onBack={() => setStep("scan")}
				/>
			</WizardStep>

			<WizardStep step="recovery">
				<TotpRecoveryStep
					recoveryCodes={recoveryCodes}
					onComplete={onComplete ?? (() => undefined)}
				/>
			</WizardStep>
		</Wizard>
	);
}
