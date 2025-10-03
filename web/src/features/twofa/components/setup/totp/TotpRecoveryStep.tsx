import { InfoPanel, WizardFooter, WizardSection } from "@/components";
import { Button } from "@/components/ui/button";
import { RecoveryCodeList } from "../../RecoveryCodeList";

interface TotpRecoveryStepProps {
	recoveryCodes?: string[];
	onComplete: () => void;
}

export function TotpRecoveryStep({
	recoveryCodes,
	onComplete,
}: TotpRecoveryStepProps) {
	return (
		<>
			<WizardSection
				title="✅ 2FA Enabled!"
				description="Save your recovery codes to regain access if you lose your device."
			>
				{recoveryCodes && (
					<RecoveryCodeList codes={recoveryCodes} showDownloadButton />
				)}
				<InfoPanel variant="success" className="text-center">
					<p className="font-semibold">
						✓ Two-factor authentication is now active
					</p>
				</InfoPanel>
			</WizardSection>
			<WizardFooter>
				<Button onClick={onComplete} className="w-full">
					Done
				</Button>
			</WizardFooter>
		</>
	);
}
