import { ButtonGroup, StatusMessage, WizardFooter, WizardSection } from "@/components";
import { Button } from "@/components/ui/button";
import { verificationCodeSchema } from "@/lib/validations";
import { VerificationInput } from "../../VerificationInput";

interface EmailVerifyStepProps {
    code: string;
    message: string;
    isVerifying: boolean;
    isResending: boolean;
    errorMessage?: string;
    onCodeChange: (value: string) => void;
    onVerify: () => void;
    onResend: () => void;
    onCancel?: () => void;
}

export function EmailVerifyStep({
    code,
    message,
    isVerifying,
    isResending,
    errorMessage,
    onCodeChange,
    onVerify,
    onResend,
    onCancel,
}: EmailVerifyStepProps) {
    return (
        <>
            <WizardSection title="Enter Email Code" description={message}>
                <VerificationInput value={code} onChange={onCodeChange} onComplete={onVerify} disabled={isVerifying} />
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
                    onClick={onVerify}
                    disabled={!verificationCodeSchema.safeParse(code).success || isVerifying}
                    className="w-full"
                >
                    {isVerifying ? "Verifying..." : "Verify & Enable Email"}
                </Button>
            </WizardFooter>
        </>
    );
}
