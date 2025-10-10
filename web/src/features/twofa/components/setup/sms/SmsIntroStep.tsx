import { Input } from "@/components/ui/input";
import { useTranslation } from "react-i18next";
import { GenericIntroStep } from "../generic";

interface SmsIntroStepProps {
	phone: string;
	onPhoneChange: (value: string) => void;
	isSending: boolean;
	errorMessage?: string;
	onSend: () => void;
	onCancel?: () => void;
}

export function SmsIntroStep(props: SmsIntroStepProps) {
	const { t } = useTranslation();
	const infoItems = t("twofa.setup.sms.info_items", {
		returnObjects: true,
	}) as string[];

	return (
		<GenericIntroStep
			config={{
				title: t("twofa.setup.sms.title"),
				description: t("twofa.setup.sms.intro"),
				customContent: (
					<div className="space-y-2 text-left">
						<label
							className="text-sm font-medium text-foreground"
							htmlFor="sms-phone"
						>
							{t("twofa.setup.sms.phone_label")}
						</label>
						<Input
							id="sms-phone"
							value={props.phone}
							onChange={(event) => props.onPhoneChange(event.target.value)}
							placeholder={t("twofa.setup.sms.phone_placeholder")}
							disabled={props.isSending}
						/>
					</div>
				),
				infoPanelTitle: t("twofa.setup.sms.info_title"),
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
