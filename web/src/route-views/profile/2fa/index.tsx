/**
 * 2FA Settings Page
 * Manage 2FA configuration, recovery codes, and trusted devices
 */

import { Button } from "@/components/ui/button";
import { ConfirmDialog, Layout } from "@/components";
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
	use2FAStatus,
	useRemoveTwoFactorMethod,
	useSetPreferredMethod,
} from "@/features/twofa";
import type { TwoFactorMethod } from "@/features/twofa";
import { useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { useTranslation } from "react-i18next";

export default function TwoFactorSettingsPage() {
	const navigate = useNavigate();
	const { t } = useTranslation();
	const { data: status, isLoading } = use2FAStatus();
	const removeMethod = useRemoveTwoFactorMethod();
	const setPreferredMethod = useSetPreferredMethod();

	const [methodToRemove, setMethodToRemove] = useState<TwoFactorMethod | null>(
		null,
	);
	const [removalError, setRemovalError] = useState<string | null>(null);
	const [switchError, setSwitchError] = useState<string | null>(null);

	const removalInProgress = removeMethod.isPending;
	const switchInProgress = setPreferredMethod.isPending;

	const handleRemovalRequest = (method: TwoFactorMethod) => {
		setRemovalError(null);
		setSwitchError(null);
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
			await removeMethod.mutateAsync(methodToRemove);
			setMethodToRemove(null);
		} catch (err) {
			setRemovalError(extractApiError(err, t("twofa.errors.remove_method")));
		}
	};

	const handleSetAsDefault = async (method: TwoFactorMethod) => {
		setSwitchError(null);
		setRemovalError(null);

		try {
			await setPreferredMethod.mutateAsync(method);
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
	const emailAddress =
		status?.email_address ?? status?.backup_email ?? undefined;

	if (isLoading) {
		return (
			<Layout.Loading
				message={t("twofa.settings.loading_title")}
				description={t("twofa.settings.loading_description")}
			/>
		);
	}

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

							{removalError && (
								<p className="text-sm text-destructive bg-destructive/10 border border-destructive/30 dark:border-destructive/40 rounded px-4 py-3 transition-colors">
									{removalError}
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
									emailAddress={emailAddress}
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
							<Button
								type="button"
								variant="link"
								onClick={() => navigate({ to: "/" })}
								className="text-sm text-muted-foreground hover:text-foreground transition-colors"
							>
								{t("common.back_home")}
							</Button>
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
