import { GenericVerifyStep } from "../generic";
import { useTranslation } from "react-i18next";

interface EmailVerifyStepProps {
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

export function EmailVerifyStep(props: EmailVerifyStepProps) {
	const { t } = useTranslation();

	return (
		<GenericVerifyStep
			config={{
				title: t("twofa.setup.email.verify_title"),
				verifyButtonText: t("twofa.setup.email.verify_button"),
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
