import { InfoPanel } from "@/components";
import { useTranslation } from "react-i18next";
import { GenericRecoveryStep } from "../generic";

interface TotpRecoveryStepProps {
	recoveryCodes?: string[];
	onComplete: () => void;
}

export function TotpRecoveryStep(props: TotpRecoveryStepProps) {
	const { t } = useTranslation();

	return (
		<GenericRecoveryStep
			config={{
				title: t("twofa.setup.recovery.enabled_title"),
				description: t("twofa.setup.recovery.description"),
				additionalContent: (
					<InfoPanel variant="success" className="text-center">
						<p className="font-semibold">
							{t("twofa.setup.recovery.enabled_message")}
						</p>
					</InfoPanel>
				),
			}}
			recoveryCodes={props.recoveryCodes}
			onComplete={props.onComplete}
		/>
	);
}
