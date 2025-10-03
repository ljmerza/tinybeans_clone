import { InfoPanel, StatusMessage, WizardFooter, WizardSection } from "@/components";
import { Button } from "@/components/ui/button";

interface EmailIntroStepProps {
    isSending: boolean;
    errorMessage?: string;
    onSend: () => void;
    onCancel?: () => void;
}

export function EmailIntroStep({ isSending, errorMessage, onSend, onCancel }: EmailIntroStepProps) {
    return (
        <>
            <WizardSection
                title="Verify by Email"
                description="We will send a 6-digit verification code to your account email."
            >
                <InfoPanel title="How it works">
                    <ul className="space-y-1 list-disc list-inside">
                        <li>We send a verification code to your primary email.</li>
                        <li>Enter the code to enable email-based 2FA.</li>
                        <li>The email method becomes your default 2FA option.</li>
                    </ul>
                </InfoPanel>
                {errorMessage && <StatusMessage variant="error">{errorMessage}</StatusMessage>}
            </WizardSection>
            <WizardFooter align={onCancel ? "between" : "end"}>
                <Button onClick={onSend} disabled={isSending} className="flex-1">
                    {isSending ? "Sending..." : "Send Verification Code"}
                </Button>
                {onCancel && (
                    <Button variant="outline" onClick={onCancel} className="flex-1">
                        Cancel
                    </Button>
                )}
            </WizardFooter>
        </>
    );
}
