import { InfoPanel, StatusMessage, WizardFooter, WizardSection } from "@/components";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface SmsIntroStepProps {
    phone: string;
    onPhoneChange: (value: string) => void;
    isSending: boolean;
    errorMessage?: string;
    onSend: () => void;
    onCancel?: () => void;
}

export function SmsIntroStep({ phone, onPhoneChange, isSending, errorMessage, onSend, onCancel }: SmsIntroStepProps) {
    return (
        <>
            <WizardSection
                title="Verify by SMS"
                description="Receive a verification code via text message. Use E.164 format (e.g. +15551234567)."
            >
                <div className="space-y-2 text-left">
                    <label className="text-sm font-medium text-gray-700" htmlFor="sms-phone">
                        Phone number
                    </label>
                    <Input
                        id="sms-phone"
                        value={phone}
                        onChange={(event) => onPhoneChange(event.target.value)}
                        placeholder="+15551234567"
                        disabled={isSending}
                    />
                </div>
                <InfoPanel title="How it works">
                    <ul className="space-y-1 list-disc list-inside">
                        <li>We send a 6-digit code via SMS.</li>
                        <li>Enter the code to enable SMS-based 2FA.</li>
                        <li>The SMS method becomes your default 2FA option.</li>
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
