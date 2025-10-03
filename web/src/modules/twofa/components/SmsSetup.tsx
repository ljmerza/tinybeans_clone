import { useState } from "react";
import { Wizard, WizardStep } from "@/components";
import { useInitialize2FASetup, useVerify2FASetup } from "../hooks";
import { SmsIntroStep } from "./setup/sms/SmsIntroStep";
import { SmsVerifyStep } from "./setup/sms/SmsVerifyStep";
import { SmsRecoveryStep } from "./setup/sms/SmsRecoveryStep";

type SetupStep = "intro" | "verify" | "recovery";

interface SmsSetupProps {
    defaultPhone?: string;
    onComplete?: () => void;
    onCancel?: () => void;
}

export function SmsSetup({ defaultPhone = "", onComplete, onCancel }: SmsSetupProps) {
    const [step, setStep] = useState<SetupStep>("intro");
    const [phone, setPhone] = useState(defaultPhone);
    const [code, setCode] = useState("");

    const initSetup = useInitialize2FASetup();
    const verifySetup = useVerify2FASetup();

    const recoveryCodes = verifySetup.data?.recovery_codes;
    const latestMessage = initSetup.data?.message ?? "Check your phone for the verification code.";

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
                            await initSetup.mutateAsync({ method: "sms", phone_number: phone.trim() });
                            setStep("verify");
                        } catch (error) {
                            console.error("SMS setup start failed:", error);
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
                    onVerify={async () => {
                        try {
                            await verifySetup.mutateAsync(code);
                            setStep("recovery");
                        } catch (error) {
                            console.error("SMS setup verification failed:", error);
                            setCode("");
                        }
                    }}
                    onResend={async () => {
                        try {
                            await initSetup.mutateAsync({ method: "sms", phone_number: phone.trim() });
                        } catch (error) {
                            console.error("SMS setup resend failed:", error);
                        }
                    }}
                    onCancel={onCancel}
                />
            </WizardStep>

            <WizardStep step="recovery">
                <SmsRecoveryStep recoveryCodes={recoveryCodes} onComplete={onComplete ?? (() => undefined)} />
            </WizardStep>
        </Wizard>
    );
}
