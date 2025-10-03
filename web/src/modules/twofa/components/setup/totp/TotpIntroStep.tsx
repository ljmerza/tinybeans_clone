import { InfoPanel, StatusMessage, WizardFooter, WizardSection } from "@/components";
import { Button } from "@/components/ui/button";

interface TotpIntroStepProps {
    isInitializing: boolean;
    errorMessage?: string;
    onStart: () => void;
    onCancel?: () => void;
}

export function TotpIntroStep({ isInitializing, errorMessage, onStart, onCancel }: TotpIntroStepProps) {
    return (
        <>
            <WizardSection
                title="Set up Authenticator App"
                description="Use an authenticator app to generate verification codes for enhanced security."
            >
                <InfoPanel title="What you'll need:">
                    <ul className="space-y-1 list-disc list-inside">
                        <li>A smartphone or tablet</li>
                        <li>An authenticator app (Google Authenticator, Authy, 1Password, etc.)</li>
                        <li>A few minutes to complete setup</li>
                    </ul>
                </InfoPanel>
                {errorMessage && <StatusMessage variant="error">{errorMessage}</StatusMessage>}
            </WizardSection>
            <WizardFooter align={onCancel ? "between" : "end"}>
                <Button onClick={onStart} disabled={isInitializing} className="flex-1">
                    {isInitializing ? "Setting up..." : "Start Setup"}
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
