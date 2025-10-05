import { GenericIntroStep } from "../generic";

interface TotpIntroStepProps {
	isInitializing: boolean;
	errorMessage?: string;
	onStart: () => void;
	onCancel?: () => void;
}

export function TotpIntroStep(props: TotpIntroStepProps) {
	return (
		<GenericIntroStep
			config={{
				title: "Set up Authenticator App",
				description:
					"Use an authenticator app to generate verification codes for enhanced security.",
				infoPanelTitle: "What you'll need:",
				infoPanelItems: [
					"A smartphone or tablet",
					"An authenticator app (Google Authenticator, Authy, 1Password, etc.)",
					"A few minutes to complete setup",
				],
				actionText: "Start Setup",
				loadingText: "Setting up...",
			}}
			isLoading={props.isInitializing}
			errorMessage={props.errorMessage}
			onAction={props.onStart}
			onCancel={props.onCancel}
		/>
	);
}
