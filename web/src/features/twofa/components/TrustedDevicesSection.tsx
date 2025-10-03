/**
 * Trusted Devices Section
 * Manage trusted devices for 2FA
 */

import { Button } from "@/components/ui/button";

interface TrustedDevicesSectionProps {
	onManage: () => void;
}

export function TrustedDevicesSection({
	onManage,
}: TrustedDevicesSectionProps) {
	return (
		<div className="bg-white rounded-lg shadow-md p-6">
			<h2 className="text-xl font-semibold mb-4">Trusted Devices</h2>
			<p className="text-gray-600 text-sm mb-4">
				Manage devices that can skip 2FA verification for 30 days.
			</p>
			<Button onClick={onManage} variant="outline">
				Manage Trusted Devices
			</Button>
		</div>
	);
}
