import { useState } from "react";
import { Wizard, WizardStep } from "@/components";
import { useInitialize2FASetup, useVerify2FASetup } from "../hooks";
import { EmailIntroStep } from "./setup/email/EmailIntroStep";
import { EmailVerifyStep } from "./setup/email/EmailVerifyStep";
import { EmailRecoveryStep } from "./setup/email/EmailRecoveryStep";

type SetupStep = "intro" | "verify" | "recovery";

interface EmailSetupProps {
    onComplete?: () => void;
    onCancel?: () => void;
}

export function EmailSetup({ onComplete, onCancel }: EmailSetupProps) {
    const [step, setStep] = useState<SetupStep>("intro");
    const [code, setCode] = useState("");

    const initSetup = useInitialize2FASetup();
    const verifySetup = useVerify2FASetup();

    const recoveryCodes = verifySetup.data?.recovery_codes;
    const latestMessage = initSetup.data?.message ?? "Check your inbox for the verification code.";

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
                            console.error("Email setup start failed:", error);
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
                            console.error("Email setup verification failed:", error);
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
                            console.error("Email setup resend failed:", error);
                        }
                    }}
                    onCancel={onCancel}
                />
            </WizardStep>

            <WizardStep step="recovery">
                <EmailRecoveryStep recoveryCodes={recoveryCodes} onComplete={onComplete ?? (() => undefined)} />
            </WizardStep>
        </Wizard>
    );
}
