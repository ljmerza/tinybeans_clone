import { useTranslation } from "react-i18next";
import { GenericIntroStep } from "../generic";

interface TotpIntroStepProps {
	isInitializing: boolean;
	errorMessage?: string;
	onStart: () => void;
	onCancel?: () => void;
}

export function TotpIntroStep(props: TotpIntroStepProps) {
	const { t } = useTranslation();
	const infoItems = t("twofa.setup.totp.info_items", {
		returnObjects: true,
	}) as string[];
	const infoPanelItems = infoItems.map((item, index) => ({
		id: `totp-info-${index}`,
		content: item,
	}));

	return (
		<GenericIntroStep
			config={{
				title: t("twofa.setup.totp.title"),
				description: t("twofa.setup.totp.intro"),
				infoPanelTitle: t("twofa.setup.totp.info_title"),
				infoPanelItems: infoPanelItems,
				actionText: t("twofa.setup.actions.start"),
				loadingText: t("twofa.setup.actions.loading"),
			}}
			isLoading={props.isInitializing}
			errorMessage={props.errorMessage}
			onAction={props.onStart}
			onCancel={props.onCancel}
		/>
	);
}
