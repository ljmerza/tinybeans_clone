/**
 * Trusted Devices Management Page
 */

import { Layout } from "@/components/Layout";
import { LoadingPage } from "@/components/LoadingSpinner";
import { Button } from "@/components/ui/button";
import {
	useRemoveTrustedDevice,
	useTrustedDevices,
} from "@/modules/twofa/hooks";
import { createFileRoute, useNavigate } from "@tanstack/react-router";

function TrustedDevicesPage() {
	const navigate = useNavigate();
	const { data, isLoading } = useTrustedDevices();
	const removeDevice = useRemoveTrustedDevice();

	const handleRemove = (deviceId: string, deviceName: string) => {
		if (
			confirm(
				`Remove "${deviceName}"?\n\nYou'll need to verify with 2FA next time you login from this device.`,
			)
		) {
			removeDevice.mutate(deviceId);
		}
	};

	if (isLoading) {
		return (
			<Layout>
				<LoadingPage message="Loading trusted devices..." fullScreen={false} />
			</Layout>
		);
	}

	const devices = data?.devices || [];

	return (
		<Layout>
			<div className="max-w-4xl mx-auto">
				<div className="bg-white rounded-lg shadow-md p-6">
					<div className="mb-6">
						<h1 className="text-2xl font-semibold mb-2">Trusted Devices</h1>
						<p className="text-gray-600 text-sm">
							These devices can skip 2FA verification for 30 days. Remove a
							device to require 2FA on next login.
						</p>
					</div>

					{devices.length === 0 ? (
						<div className="text-center py-12">
							<div className="text-6xl mb-4">🔒</div>
							<p className="text-gray-600 mb-2">No trusted devices</p>
							<p className="text-sm text-gray-500">
								Enable "Remember this device" during 2FA verification to add
								trusted devices
							</p>
						</div>
					) : (
						<div className="space-y-4">
							{devices.map((device) => (
								<div
									key={device.device_id}
									className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
								>
									<div className="flex items-start justify-between">
										<div className="flex-1">
											<h3 className="font-semibold text-lg mb-2">
												{device.device_name}
											</h3>
											<div className="space-y-1 text-sm text-gray-600">
												<div className="flex items-center gap-2">
													<span className="font-medium">IP Address:</span>
													<span className="font-mono">{device.ip_address}</span>
												</div>
												<div className="flex items-center gap-2">
													<span className="font-medium">Last used:</span>
													<span>
														{new Date(device.last_used_at).toLocaleString()}
													</span>
												</div>
												<div className="flex items-center gap-2">
													<span className="font-medium">Expires:</span>
													<span>
														{new Date(device.expires_at).toLocaleDateString()}
													</span>
												</div>
												<div className="flex items-center gap-2">
													<span className="font-medium">Added:</span>
													<span>
														{new Date(device.created_at).toLocaleDateString()}
													</span>
												</div>
											</div>
										</div>

										<Button
											variant="outline"
											size="sm"
											onClick={() =>
												handleRemove(device.device_id, device.device_name)
											}
											disabled={removeDevice.isPending}
											className="text-red-600 border-red-300 hover:bg-red-50 ml-4"
										>
											{removeDevice.isPending ? "Removing..." : "Remove"}
										</Button>
									</div>
								</div>
							))}
						</div>
					)}

					<div className="mt-6 pt-6 border-t flex justify-between">
						<button
							onClick={() => navigate({ to: "/2fa/settings" })}
							className="text-sm text-gray-600 hover:text-gray-800"
						>
							← Back to 2FA Settings
						</button>

						<p className="text-xs text-gray-500">
							{devices.length} trusted{" "}
							{devices.length === 1 ? "device" : "devices"}
						</p>
					</div>
				</div>
			</div>
		</Layout>
	);
}

export const Route = createFileRoute("/2fa/trusted-devices")({
	component: TrustedDevicesPage,
});
