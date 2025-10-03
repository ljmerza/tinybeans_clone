import { useState } from "react";
import { Wizard, WizardStep } from "@/components";
import { useInitialize2FASetup, useVerify2FASetup } from "../hooks";
import { TotpIntroStep } from "./setup/totp/TotpIntroStep";
import { TotpScanStep } from "./setup/totp/TotpScanStep";
import { TotpVerifyStep } from "./setup/totp/TotpVerifyStep";
import { TotpRecoveryStep } from "./setup/totp/TotpRecoveryStep";

type SetupStep = "intro" | "scan" | "verify" | "recovery";

interface TotpSetupProps {
	onComplete?: () => void;
	onCancel?: () => void;
}

export function TotpSetup({ onComplete, onCancel }: TotpSetupProps) {
	const [step, setStep] = useState<SetupStep>("intro");
	const [code, setCode] = useState("");

	const initSetup = useInitialize2FASetup();
	const verifySetup = useVerify2FASetup();

	const setupData = initSetup.data;
	const recoveryCodes = verifySetup.data?.recovery_codes;

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
							console.error("Setup initialization failed:", error);
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
							console.error("Verification failed:", error);
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
