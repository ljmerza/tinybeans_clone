import { GenericRecoveryStep } from "../generic";

interface SmsRecoveryStepProps {
	recoveryCodes?: string[];
	onComplete: () => void;
}

export function SmsRecoveryStep(props: SmsRecoveryStepProps) {
	return (
		<GenericRecoveryStep
			config={{
				title: "✅ SMS 2FA Enabled",
				description:
					"Save your recovery codes in a safe place in case you can't receive texts.",
			}}
			recoveryCodes={props.recoveryCodes}
			onComplete={props.onComplete}
		/>
	);
}
