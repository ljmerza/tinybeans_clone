import { WizardFooter, WizardSection } from "@/components";
import { Button } from "@/components/ui/button";
import { RecoveryCodeList } from "../../RecoveryCodeList";

interface SmsRecoveryStepProps {
	recoveryCodes?: string[];
	onComplete: () => void;
}

export function SmsRecoveryStep({
	recoveryCodes,
	onComplete,
}: SmsRecoveryStepProps) {
	return (
		<>
			<WizardSection
				title="✅ SMS 2FA Enabled"
				description="Save your recovery codes in a safe place in case you can’t receive texts."
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
