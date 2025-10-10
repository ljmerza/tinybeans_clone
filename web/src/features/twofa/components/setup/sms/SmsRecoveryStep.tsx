import { useTranslation } from "react-i18next";
import { GenericRecoveryStep } from "../generic";

interface SmsRecoveryStepProps {
	recoveryCodes?: string[];
	onComplete: () => void;
}

export function SmsRecoveryStep(props: SmsRecoveryStepProps) {
	const { t } = useTranslation();

	return (
		<GenericRecoveryStep
			config={{
				title: t("twofa.setup.sms.recovery_title"),
				description: t("twofa.setup.sms.recovery_description"),
			}}
			recoveryCodes={props.recoveryCodes}
			onComplete={props.onComplete}
		/>
	);
}
