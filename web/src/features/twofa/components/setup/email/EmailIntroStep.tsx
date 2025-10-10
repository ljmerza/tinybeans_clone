import { useTranslation } from "react-i18next";
import { GenericIntroStep } from "../generic";

interface EmailIntroStepProps {
	isSending: boolean;
	errorMessage?: string;
	onSend: () => void;
	onCancel?: () => void;
}

export function EmailIntroStep(props: EmailIntroStepProps) {
	const { t } = useTranslation();
	const infoItems = t("twofa.setup.email.info_items", {
		returnObjects: true,
	}) as string[];

	return (
		<GenericIntroStep
			config={{
				title: t("twofa.setup.email.title"),
				description: t("twofa.setup.email.intro"),
				infoPanelTitle: t("twofa.setup.email.info_title"),
				infoPanelItems: infoItems,
				actionText: t("twofa.setup.actions.start"),
				loadingText: t("twofa.setup.actions.loading"),
			}}
			isLoading={props.isSending}
			errorMessage={props.errorMessage}
			onAction={props.onSend}
			onCancel={props.onCancel}
		/>
	);
}
