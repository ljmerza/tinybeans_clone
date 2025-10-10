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
		<div className="bg-card text-card-foreground border border-border rounded-lg shadow-md p-6 transition-colors">
			<h2 className="text-xl font-semibold text-foreground mb-4">
				{t("twofa.settings.trusted_devices.title")}
			</h2>
			<p className="text-muted-foreground text-sm mb-4">
				{t("twofa.settings.trusted_devices.description")}
			</p>
			<Button onClick={onManage} variant="outline">
				{t("twofa.settings.trusted_devices.manage_action")}
			</Button>
		</div>
	);
}
