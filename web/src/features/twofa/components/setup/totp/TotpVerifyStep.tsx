import { GenericVerifyStep } from "../generic";
import { useTranslation } from "react-i18next";

interface TotpVerifyStepProps {
	code: string;
	isVerifying: boolean;
	errorMessage?: string;
	onCodeChange: (value: string) => void;
	onVerify: (value?: string) => void;
	onBack: () => void;
}

export function TotpVerifyStep(props: TotpVerifyStepProps) {
  const { t } = useTranslation();

  return (
    <GenericVerifyStep
      config={{
        title: t("twofa.setup.totp.verify_title"),
        verifyButtonText: t("twofa.setup.actions.verify_enable"),
        loadingText: t("twofa.setup.actions.verifying"),
        showResend: false,
        backButtonText: t("twofa.setup.actions.back_to_scan"),
      }}
      code={props.code}
      message={t("twofa.setup.totp.enter_code")}
			isVerifying={props.isVerifying}
			errorMessage={props.errorMessage}
			onCodeChange={props.onCodeChange}
			onVerify={props.onVerify}
			onSecondaryAction={props.onBack}
		/>
	);
}
