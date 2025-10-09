import { GenericIntroStep } from "../generic";
import { useTranslation } from "react-i18next";

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

  return (
    <GenericIntroStep
      config={{
        title: t("twofa.setup.totp.title"),
        description: t("twofa.setup.totp.intro"),
        infoPanelTitle: t("twofa.setup.totp.info_title"),
        infoPanelItems: infoItems,
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
