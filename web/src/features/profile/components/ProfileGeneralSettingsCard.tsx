import { useTranslation } from "react-i18next";

export function ProfileGeneralSettingsCard() {
	const { t } = useTranslation();

	return (
		<div className="space-y-6">
			<div className="bg-white rounded-lg shadow-md p-6 space-y-2">
				<h2 className="text-xl font-semibold">
					{t("twofa.settings.general.title")}
				</h2>
				<p className="text-sm text-gray-600">
					{t("twofa.settings.general.description")}
				</p>
			</div>
		</div>
	);
}
