/**
 * Trusted Devices Management Page
 */

import { EmptyState, Layout } from "@/components";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { requireAuth, requireCircleOnboardingComplete } from "@/features/auth";
import {
	twoFaKeys,
	twoFactorServices,
	useAddTrustedDevice,
	useRemoveTrustedDevice,
	useTrustedDevices,
} from "@/features/twofa";
import type { TrustedDevicesResponse } from "@/features/twofa";
import type { QueryClient } from "@tanstack/react-query";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { useTranslation } from "react-i18next";

function TrustedDevicesPage() {
	const navigate = useNavigate();
	const { data, isLoading } = useTrustedDevices();
	const removeDevice = useRemoveTrustedDevice();
	const addDevice = useAddTrustedDevice();
	const { t } = useTranslation();
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
				message={t("twofa.trusted_devices.loading_title")}
				description={t("twofa.trusted_devices.loading_description")}
			/>
		);
	}

	const devices = data?.devices || [];

	return (
		<Layout>
			<div className="max-w-4xl mx-auto">
				<div className="bg-card text-card-foreground border border-border rounded-lg shadow-md p-6 transition-colors">
					<div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
						<div>
							<h1 className="text-2xl font-semibold text-foreground mb-2">
								{t("twofa.trusted_devices.title")}
							</h1>
							<p className="text-muted-foreground text-sm">
								{t("twofa.trusted_devices.subtitle")}
							</p>
						</div>
						<Button
							variant="secondary"
							onClick={() => addDevice.mutate()}
							isLoading={addDevice.isPending}
							className="w-full sm:w-auto"
						>
							{addDevice.isPending
								? t("twofa.trusted_devices.add_loading")
								: t("twofa.trusted_devices.add_button")}
						</Button>
					</div>

					{devices.length === 0 ? (
						<EmptyState
							icon={
								<span role="img" aria-hidden className="text-5xl">
									🔒
								</span>
							}
							title={t("twofa.trusted_devices.empty_title")}
							description={t("twofa.trusted_devices.empty_description")}
							actions={
								<Button
									variant="secondary"
									onClick={() => addDevice.mutate()}
									isLoading={addDevice.isPending}
								>
									{addDevice.isPending
										? t("twofa.trusted_devices.add_loading")
										: t("twofa.trusted_devices.add_button")}
								</Button>
							}
						>
							<p className="text-sm text-muted-foreground max-w-prose">
								{t("twofa.trusted_devices.empty_helper")}
							</p>
						</EmptyState>
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
														{t("twofa.trusted_devices.metadata.ip")}
													</span>
													<span className="font-mono">{device.ip_address}</span>
												</div>
												<div className="flex items-center gap-2">
													<span className="font-medium text-foreground">
														{t("twofa.trusted_devices.metadata.last_used")}
													</span>
													<span>
														{new Date(device.last_used_at).toLocaleString()}
													</span>
												</div>
												<div className="flex items-center gap-2">
													<span className="font-medium text-foreground">
														{t("twofa.trusted_devices.metadata.expires")}
													</span>
													<span>
														{new Date(device.expires_at).toLocaleDateString()}
													</span>
												</div>
												<div className="flex items-center gap-2">
													<span className="font-medium text-foreground">
														{t("twofa.trusted_devices.metadata.added")}
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
											isLoading={
												removeDevice.isPending &&
												deviceToRemove?.id === device.device_id
											}
											className="ml-4"
										>
											{removeDevice.isPending &&
											deviceToRemove?.id === device.device_id
												? t("twofa.trusted_devices.remove_loading")
												: t("twofa.trusted_devices.remove_button")}
										</Button>
									</div>
								</div>
							))}
						</div>
					)}

					<div className="mt-6 pt-6 border-t border-border flex justify-between">
						<Button
							type="button"
							variant="link"
							onClick={() => navigate({ to: "/profile/2fa" })}
							className="text-sm text-muted-foreground hover:text-foreground transition-colors"
						>
							{t("twofa.trusted_devices.back_to_settings")}
						</Button>

						<p className="text-xs text-muted-foreground">
							{t("twofa.trusted_devices.count_label", {
								count: devices.length,
							})}
						</p>
					</div>
				</div>
			</div>

			<ConfirmDialog
				open={deviceToRemove !== null}
				onOpenChange={(open) => !open && setDeviceToRemove(null)}
				title={t("twofa.trusted_devices.remove_confirm_title", {
					name: deviceToRemove?.name ?? "",
				})}
				description={t("twofa.trusted_devices.remove_confirm_description")}
				confirmLabel={t("twofa.trusted_devices.remove_confirm_cta")}
				variant="destructive"
				isLoading={removeDevice.isPending}
				onConfirm={confirmRemove}
			/>
		</Layout>
	);
}

export const Route = createFileRoute("/profile/2fa/trusted-devices")({
	beforeLoad: async (args) => {
		await requireAuth(args);
		await requireCircleOnboardingComplete(args);
	},
	loader: ({ context }) => {
		const { queryClient } = context as { queryClient: QueryClient };
		return queryClient.ensureQueryData({
			queryKey: twoFaKeys.trustedDevices(),
			queryFn: () => twoFactorServices.getTrustedDevices(),
		});
	},
	component: TrustedDevicesPage,
});
