/**
 * Trusted Devices Management Page
 */

import { Layout } from "@/components";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import {
	twoFaKeys,
	twoFactorApi,
	useRemoveTrustedDevice,
	useTrustedDevices,
} from "@/features/twofa";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";

function TrustedDevicesPage() {
	const navigate = useNavigate();
	const { data, isLoading } = useTrustedDevices();
	const removeDevice = useRemoveTrustedDevice();
	const [deviceToRemove, setDeviceToRemove] = useState<{
		id: string;
		name: string;
	} | null>(null);

	const handleRemove = (deviceId: string, deviceName: string) => {
		setDeviceToRemove({ id: deviceId, name: deviceName });
	};

	const confirmRemove = () => {
		if (deviceToRemove) {
			removeDevice.mutate(deviceToRemove.id);
			setDeviceToRemove(null);
		}
	};

	if (isLoading) {
		return (
			<Layout.Loading
				message="Loading trusted devices..."
				description="Fetching the devices that have been marked as trusted."
			/>
		);
	}

	const devices = data?.devices || [];

	return (
		<Layout>
			<div className="max-w-4xl mx-auto">
				<div className="bg-card text-card-foreground border border-border rounded-lg shadow-md p-6 transition-colors">
					<div className="mb-6">
						<h1 className="text-2xl font-semibold text-foreground mb-2">
							Trusted Devices
						</h1>
						<p className="text-muted-foreground text-sm">
							These devices can skip 2FA verification for 30 days. Remove a
							device to require 2FA on next login.
						</p>
					</div>

					{devices.length === 0 ? (
						<div className="text-center py-12">
							<div className="text-6xl mb-4">🔒</div>
							<p className="text-muted-foreground mb-2">No trusted devices</p>
							<p className="text-sm text-muted-foreground">
								Enable "Remember this device" during 2FA verification to add
								trusted devices
							</p>
						</div>
					) : (
						<div className="space-y-4">
							{devices.map((device) => (
								<div
									key={device.device_id}
									className="border border-border rounded-lg p-4 hover:shadow-md transition-shadow transition-colors"
								>
									<div className="flex items-start justify-between">
										<div className="flex-1">
											<h3 className="font-semibold text-lg text-foreground mb-2">
												{device.device_name}
											</h3>
											<div className="space-y-1 text-sm text-muted-foreground">
												<div className="flex items-center gap-2">
													<span className="font-medium text-foreground">
														IP Address:
													</span>
													<span className="font-mono">{device.ip_address}</span>
												</div>
												<div className="flex items-center gap-2">
													<span className="font-medium text-foreground">
														Last used:
													</span>
													<span>
														{new Date(device.last_used_at).toLocaleString()}
													</span>
												</div>
												<div className="flex items-center gap-2">
													<span className="font-medium text-foreground">
														Expires:
													</span>
													<span>
														{new Date(device.expires_at).toLocaleDateString()}
													</span>
												</div>
												<div className="flex items-center gap-2">
													<span className="font-medium text-foreground">
														Added:
													</span>
													<span>
														{new Date(device.created_at).toLocaleDateString()}
													</span>
												</div>
											</div>
										</div>

										<Button
											variant="destructive"
											size="sm"
											onClick={() =>
												handleRemove(device.device_id, device.device_name)
											}
											disabled={removeDevice.isPending}
											className="ml-4"
										>
											{removeDevice.isPending ? "Removing..." : "Remove"}
										</Button>
									</div>
								</div>
							))}
						</div>
					)}

					<div className="mt-6 pt-6 border-t border-border flex justify-between">
						<button
							type="button"
							onClick={() => navigate({ to: "/profile/2fa" })}
							className="text-sm text-muted-foreground hover:text-foreground transition-colors"
						>
							← Back to 2FA Settings
						</button>

						<p className="text-xs text-muted-foreground">
							{devices.length} trusted{" "}
							{devices.length === 1 ? "device" : "devices"}
						</p>
					</div>
				</div>
			</div>

			<ConfirmDialog
				open={deviceToRemove !== null}
				onOpenChange={(open) => !open && setDeviceToRemove(null)}
				title={`Remove "${deviceToRemove?.name}"?`}
				description="You'll need to verify with 2FA next time you login from this device."
				confirmLabel="Remove"
				variant="destructive"
				isLoading={removeDevice.isPending}
				onConfirm={confirmRemove}
			/>
		</Layout>
	);
}

export const Route = createFileRoute("/profile/2fa/trusted-devices")({
	loader: ({ context: { queryClient } }) =>
		queryClient.ensureQueryData({
			queryKey: twoFaKeys.trustedDevices(),
			queryFn: () => twoFactorApi.getTrustedDevices(),
		}),
	component: TrustedDevicesPage,
});
