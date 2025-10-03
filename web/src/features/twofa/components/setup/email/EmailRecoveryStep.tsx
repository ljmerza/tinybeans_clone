import { WizardFooter, WizardSection } from "@/components";
import { Button } from "@/components/ui/button";
import { RecoveryCodeList } from "../../RecoveryCodeList";

interface EmailRecoveryStepProps {
	recoveryCodes?: string[];
	onComplete: () => void;
}

export function EmailRecoveryStep({
	recoveryCodes,
	onComplete,
}: EmailRecoveryStepProps) {
	return (
		<>
			<WizardSection
				title="✅ Email 2FA Enabled"
				description="Save your recovery codes to keep access if you can’t reach your email."
			>
				{recoveryCodes && (
					<RecoveryCodeList codes={recoveryCodes} showDownloadButton />
				)}
			</WizardSection>
			<WizardFooter>
				<Button onClick={onComplete} className="w-full">
					Done
				</Button>
			</WizardFooter>
		</>
	);
}
