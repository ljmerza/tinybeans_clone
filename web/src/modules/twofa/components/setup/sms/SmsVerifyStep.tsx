import { ButtonGroup, StatusMessage, WizardFooter, WizardSection } from "@/components";
import { Button } from "@/components/ui/button";
import { verificationCodeSchema } from "@/lib/validations";
import { VerificationInput } from "../../VerificationInput";

interface SmsVerifyStepProps {
    code: string;
    message: string;
    isVerifying: boolean;
    isResending: boolean;
    errorMessage?: string;
    onCodeChange: (value: string) => void;
    onVerify: (value?: string) => void;
    onResend: () => void;
    onCancel?: () => void;
}

export function SmsVerifyStep({
    code,
    message,
    isVerifying,
    isResending,
    errorMessage,
    onCodeChange,
    onVerify,
    onResend,
    onCancel,
}: SmsVerifyStepProps) {
    return (
        <>
            <WizardSection title="Enter SMS Code" description={message}>
                <VerificationInput value={code} onChange={onCodeChange} onComplete={(val) => onVerify(val)} disabled={isVerifying} />
                <ButtonGroup className="flex-col sm:flex-row sm:justify-between">
                    <Button onClick={onResend} variant="ghost" disabled={isResending} className="sm:w-auto">
                        Resend Code
                    </Button>
                    {onCancel && (
                        <Button variant="outline" onClick={onCancel} className="sm:w-auto">
                            Cancel
                        </Button>
                    )}
                </ButtonGroup>
                {errorMessage && (
                    <StatusMessage variant="error" align="center">
                        {errorMessage}
                    </StatusMessage>
                )}
            </WizardSection>
            <WizardFooter>
                <Button
                    onClick={() => onVerify()}
                    disabled={!verificationCodeSchema.safeParse(code).success || isVerifying}
                    className="w-full"
                >
                    {isVerifying ? "Verifying..." : "Verify & Enable SMS"}
                </Button>
            </WizardFooter>
        </>
    );
}
