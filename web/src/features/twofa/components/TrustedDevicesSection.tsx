/**
 * Trusted Devices Section
 * Manage trusted devices for 2FA
 */

import { Button } from "@/components/ui/button";
import { useTranslation } from "react-i18next";

interface TrustedDevicesSectionProps {
	onManage: () => void;
}

export function TrustedDevicesSection({
	onManage,
}: TrustedDevicesSectionProps) {
	const { t } = useTranslation();

	return (
		<div className="bg-white rounded-lg shadow-md p-6">
			<h2 className="text-xl font-semibold mb-4">
				{t("twofa.settings.trusted_devices.title")}
			</h2>
			<p className="text-gray-600 text-sm mb-4">
				{t("twofa.settings.trusted_devices.description")}
			</p>
			<Button onClick={onManage} variant="outline">
				{t("twofa.settings.trusted_devices.manage_action")}
			</Button>
		</div>
	);
}
