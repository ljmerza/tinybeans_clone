import { GenericVerifyStep } from "../generic";

interface TotpVerifyStepProps {
	code: string;
	isVerifying: boolean;
	errorMessage?: string;
	onCodeChange: (value: string) => void;
	onVerify: (value?: string) => void;
	onBack: () => void;
}

export function TotpVerifyStep(props: TotpVerifyStepProps) {
	return (
		<GenericVerifyStep
			config={{
				title: "Verify Setup",
				verifyButtonText: "Verify & Enable 2FA",
				loadingText: "Verifying...",
				showResend: false,
				backButtonText: "Back to QR Code",
			}}
			code={props.code}
			message="Enter the 6-digit code from your authenticator app."
			isVerifying={props.isVerifying}
			errorMessage={props.errorMessage}
			onCodeChange={props.onCodeChange}
			onVerify={props.onVerify}
			onSecondaryAction={props.onBack}
		/>
	);
}
