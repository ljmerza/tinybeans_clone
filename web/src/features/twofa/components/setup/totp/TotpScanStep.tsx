import { StatusMessage, WizardFooter, WizardSection } from "@/components";
import { Button } from "@/components/ui/button";
import { useTranslation } from "react-i18next";
import { QRCodeDisplay } from "../../QRCodeDisplay";

interface TotpScanStepProps {
	qrCodeImage?: string;
	secret?: string;
	onContinue: () => void;
}

export function TotpScanStep({
	qrCodeImage,
	secret,
	onContinue,
}: TotpScanStepProps) {
	const { t } = useTranslation();

	return (
		<>
			<WizardSection
				title={t("twofa.setup.totp.scan")}
				description={t("twofa.setup.totp.scan_instructions")}
			>
				{qrCodeImage && secret ? (
					<QRCodeDisplay qrCodeImage={qrCodeImage} secret={secret} />
				) : (
					<StatusMessage variant="error" align="center">
						{t("twofa.errors.qr_load")}
					</StatusMessage>
				)}
			</WizardSection>
			<WizardFooter>
				<Button onClick={onContinue} className="w-full">
					{t("twofa.setup.actions.scan_complete")}
				</Button>
			</WizardFooter>
		</>
	);
}
