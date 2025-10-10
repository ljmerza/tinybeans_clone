/**
 * 2FA Settings Page
 * Manage 2FA configuration, recovery codes, and trusted devices
 */

import { ConfirmDialog, Layout } from "@/components";
import type { QueryClient } from "@tanstack/react-query";
import { extractApiError } from "@/features/auth/utils";
import {
	ProfileGeneralSettingsCard,
	ProfileSettingsTabs,
} from "@/features/profile";
import {
	EmailMethodCard,
	SmsMethodCard,
	TotpMethodCard,
	TwoFactorEnabledSettings,
	TwoFactorStatusHeader,
	twoFaKeys,
	twoFactorApi,
	use2FAStatus,
	useRemoveTwoFactorMethod,
	useSetPreferredMethod,
} from "@/features/twofa";
import type { TwoFactorMethod } from "@/features/twofa";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { useTranslation } from "react-i18next";

const twoFactorSettingsPath = "/profile/2fa/" as const;

function TwoFactorSettingsPage() {
	const navigate = useNavigate();
	const { t } = useTranslation();
	const { data: status, isLoading } = use2FAStatus();
	const removeMethod = useRemoveTwoFactorMethod();
	const setPreferredMethod = useSetPreferredMethod();

	const [methodToRemove, setMethodToRemove] = useState<TwoFactorMethod | null>(
		null,
	);
	const [removalMessage, setRemovalMessage] = useState<string | null>(null);
	const [removalError, setRemovalError] = useState<string | null>(null);
	const [switchMessage, setSwitchMessage] = useState<string | null>(null);
	const [switchError, setSwitchError] = useState<string | null>(null);

	const removalInProgress = removeMethod.isPending;
	const switchInProgress = setPreferredMethod.isPending;

	const handleRemovalRequest = (method: TwoFactorMethod) => {
		setRemovalError(null);
		setRemovalMessage(null);
		setSwitchError(null);
		setSwitchMessage(null);
		setMethodToRemove(method);
	};

	const handleRemovalCancel = () => {
		setMethodToRemove(null);
		setRemovalError(null);
	};

	const handleRemovalConfirm = async () => {
		if (!methodToRemove) return;
		setRemovalError(null);
		try {
			const result = await removeMethod.mutateAsync(methodToRemove);
			setRemovalMessage(result?.message ?? t("twofa.messages.method_removed"));
			setMethodToRemove(null);
		} catch (err) {
			setRemovalError(extractApiError(err, t("twofa.errors.remove_method")));
		}
	};

	const handleSetAsDefault = async (method: TwoFactorMethod) => {
		setSwitchError(null);
		setSwitchMessage(null);
		setRemovalError(null);
		setRemovalMessage(null);

		try {
			const result = await setPreferredMethod.mutateAsync(method);
			setSwitchMessage(
				result?.message ?? t("twofa.messages.default_method_updated"),
			);
		} catch (err) {
			setSwitchError(
				extractApiError(err, t("twofa.errors.update_default_method")),
			);
		}
	};

	const preferredMethod = status?.preferred_method ?? null;
	const totpConfigured = Boolean(status?.has_totp);
	const smsConfigured = Boolean(status?.has_sms);
	const emailConfigured = Boolean(status?.has_email);
	const phoneNumber = status?.phone_number;

	if (isLoading) {
		return (
			<Layout.Loading
				message={t("twofa.settings.loading_title")}
				description={t("twofa.settings.loading_description")}
			/>
		);
	}

	// Always show consolidated setup on settings page. If 2FA is not enabled, show an inline callout instead of routing to a separate /profile/2fa/setup page.
	// This ensures there is no dependency on a non-existent setup route.

	if (!status) {
		return (
			<Layout.Error
				title={t("twofa.title")}
				description={t("twofa.errors.load_settings")}
				actionLabel={t("common.retry")}
				onAction={() => navigate({ to: "/profile/2fa" })}
			/>
		);
	}

	return (
		<Layout>
			<ProfileSettingsTabs
				general={<ProfileGeneralSettingsCard />}
				twoFactor={
					<div className="space-y-6">
						<TwoFactorStatusHeader status={status} />

						<div className="bg-card text-card-foreground border border-border rounded-lg shadow-md p-6 space-y-6 transition-colors">
							<div className="flex items-start justify-between">
								<div>
									<h2 className="text-xl font-semibold text-foreground mb-1">
										{t("twofa.settings.manage_title")}
									</h2>
									<p className="text-sm text-muted-foreground">
										{t("twofa.settings.manage_description")}
									</p>
								</div>
							</div>

							{!status.is_enabled && (
								<div className="bg-amber-500/15 border border-amber-500/30 dark:border-amber-500/40 text-sm rounded-lg p-4 transition-colors">
									<p className="font-semibold">
										{t("twofa.settings.not_enabled_title")}
									</p>
									<p className="text-muted-foreground">
										{t("twofa.settings.not_enabled_description")}
									</p>
								</div>
							)}

							{removalMessage && (
								<p className="text-sm text-emerald-700 dark:text-emerald-300 bg-emerald-500/10 border border-emerald-500/20 rounded px-4 py-3 transition-colors">
									{removalMessage}
								</p>
							)}

							{removalError && (
								<p className="text-sm text-destructive bg-destructive/10 border border-destructive/30 dark:border-destructive/40 rounded px-4 py-3 transition-colors">
									{removalError}
								</p>
							)}

							{switchMessage && (
								<p className="text-sm text-emerald-700 dark:text-emerald-300 bg-emerald-500/10 border border-emerald-500/20 rounded px-4 py-3 transition-colors">
									{switchMessage}
								</p>
							)}

							{switchError && (
								<p className="text-sm text-destructive bg-destructive/10 border border-destructive/30 dark:border-destructive/40 rounded px-4 py-3 transition-colors">
									{switchError}
								</p>
							)}

							<div className="space-y-4">
								<TotpMethodCard
									isCurrent={preferredMethod === "totp"}
									configured={totpConfigured}
									removalInProgress={removalInProgress}
									methodToRemove={methodToRemove}
									onSetup={() => navigate({ to: "/profile/2fa/setup/totp" })}
									onRequestRemoval={() => handleRemovalRequest("totp")}
									onSetAsDefault={() => handleSetAsDefault("totp")}
									setAsDefaultInProgress={switchInProgress}
								/>

								<EmailMethodCard
									isCurrent={preferredMethod === "email"}
									configured={emailConfigured}
									onSetup={() => navigate({ to: "/profile/2fa/setup/email" })}
									onSetAsDefault={() => handleSetAsDefault("email")}
									setAsDefaultInProgress={switchInProgress}
									onRequestRemoval={() => handleRemovalRequest("email")}
									removalInProgress={removalInProgress}
									methodToRemove={methodToRemove}
								/>

								<SmsMethodCard
									isCurrent={preferredMethod === "sms"}
									configured={smsConfigured}
									phoneNumber={phoneNumber}
									removalInProgress={removalInProgress}
									methodToRemove={methodToRemove}
									onSetup={() => navigate({ to: "/profile/2fa/setup/sms" })}
									onRequestRemoval={() => handleRemovalRequest("sms")}
									onSetAsDefault={() => handleSetAsDefault("sms")}
									setAsDefaultInProgress={switchInProgress}
								/>
							</div>
						</div>

						{status.is_enabled && <TwoFactorEnabledSettings />}

						<div className="text-center">
							<button
								type="button"
								onClick={() => navigate({ to: "/" })}
								className="text-sm text-muted-foreground hover:text-foreground transition-colors"
							>
								{t("common.back_home")}
							</button>
						</div>
					</div>
				}
			/>

			{(() => {
				const methodLabel = methodToRemove
					? t(`twofa.methods.${methodToRemove}`)
					: "";
				const removalDescription = methodToRemove
					? t(`twofa.settings.remove_description.${methodToRemove}`)
					: "";

				return (
					<ConfirmDialog
						open={!!methodToRemove}
						onOpenChange={(open) => !open && handleRemovalCancel()}
						title={
							methodToRemove
								? t("twofa.settings.remove_title", { method: methodLabel })
								: ""
						}
						description={removalDescription}
						confirmLabel={t("common.remove")}
						cancelLabel={t("common.cancel")}
						variant="destructive"
						isLoading={removalInProgress}
						onConfirm={handleRemovalConfirm}
						onCancel={handleRemovalCancel}
					/>
				);
			})()}
		</Layout>
	);
}

export const Route = createFileRoute(twoFactorSettingsPath)({
	loader: ({ context }) => {
		const { queryClient } = context as { queryClient: QueryClient };
		return queryClient.ensureQueryData({
			queryKey: twoFaKeys.status(),
			queryFn: () => twoFactorApi.getStatus(),
		});
	},
	component: TwoFactorSettingsPage,
});
