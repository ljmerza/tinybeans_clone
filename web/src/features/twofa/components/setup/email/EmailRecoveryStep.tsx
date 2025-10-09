import { GenericRecoveryStep } from "../generic";
import { useTranslation } from "react-i18next";

interface EmailRecoveryStepProps {
	recoveryCodes?: string[];
	onComplete: () => void;
}

export function EmailRecoveryStep(props: EmailRecoveryStepProps) {
	const { t } = useTranslation();

	return (
		<GenericRecoveryStep
			config={{
				title: t("twofa.setup.email.recovery_title"),
				description: t("twofa.setup.email.recovery_description"),
			}}
			recoveryCodes={props.recoveryCodes}
			onComplete={props.onComplete}
		/>
	);
}
