import { useTranslation } from "react-i18next";
import { GenericVerifyStep } from "../generic";

interface SmsVerifyStepProps {
	code: string;
	message: string;
	isVerifying: boolean;
	isResending: boolean;
	errorMessage?: string;
	onCodeChange: (value: string) => void;
	onVerify: (value?: string) => void;
	onResend: () => void;
	onCancel?: () => void;
}

export function SmsVerifyStep(props: SmsVerifyStepProps) {
	const { t } = useTranslation();

	return (
		<GenericVerifyStep
			config={{
				title: t("twofa.setup.sms.verify_title"),
				verifyButtonText: t("twofa.setup.sms.verify_button"),
				loadingText: t("twofa.setup.actions.verifying"),
				showResend: true,
				resendButtonText: t("twofa.setup.actions.resend"),
			}}
			code={props.code}
			message={props.message}
			isVerifying={props.isVerifying}
			isResending={props.isResending}
			errorMessage={props.errorMessage}
			onCodeChange={props.onCodeChange}
			onVerify={props.onVerify}
			onResend={props.onResend}
			onSecondaryAction={props.onCancel}
		/>
	);
}
