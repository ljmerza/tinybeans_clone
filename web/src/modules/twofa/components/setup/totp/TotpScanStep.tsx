import { StatusMessage, Wizard, WizardFooter, WizardSection } from "@/components";
import { Button } from "@/components/ui/button";
import { QRCodeDisplay } from "../../QRCodeDisplay";

interface TotpScanStepProps {
    qrCodeImage?: string;
    secret?: string;
    onContinue: () => void;
}

export function TotpScanStep({ qrCodeImage, secret, onContinue }: TotpScanStepProps) {
    const footer = (
        <WizardFooter>
            <Button onClick={onContinue} className="w-full">
                I've Scanned the Code
            </Button>
        </WizardFooter>
    );

    return (
        <Wizard footer={footer}>
            <WizardSection title="Scan QR Code" description="Open your authenticator app and scan this QR code.">
                {qrCodeImage && secret ? (
                    <QRCodeDisplay qrCodeImage={qrCodeImage} secret={secret} />
                ) : (
                    <StatusMessage variant="error" align="center">
                        We couldn’t load your QR code. Please restart the setup process.
                    </StatusMessage>
                )}
            </WizardSection>
        </Wizard>
    );
}
