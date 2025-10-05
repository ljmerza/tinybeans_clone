import { GenericIntroStep } from "../generic";

interface EmailIntroStepProps {
	isSending: boolean;
	errorMessage?: string;
	onSend: () => void;
	onCancel?: () => void;
}

export function EmailIntroStep(props: EmailIntroStepProps) {
	return (
		<GenericIntroStep
			config={{
				title: "Verify by Email",
				description: "We will send a 6-digit verification code to your account email.",
				infoPanelTitle: "How it works",
				infoPanelItems: [
					"We send a verification code to your primary email.",
					"Enter the code to enable email-based 2FA.",
					"The email method becomes your default 2FA option.",
				],
				actionText: "Send Verification Code",
				loadingText: "Sending...",
			}}
			isLoading={props.isSending}
			errorMessage={props.errorMessage}
			onAction={props.onSend}
			onCancel={props.onCancel}
		/>
	);
}
