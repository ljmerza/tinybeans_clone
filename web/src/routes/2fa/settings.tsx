/**
 * 2FA Settings Page
 * Manage 2FA configuration, recovery codes, and trusted devices
 */

import { ConfirmDialog, Layout } from "@/components";
import { TwoFactorEnabledSettings } from "@/modules/twofa/components/TwoFactorEnabledSettings";
import { TwoFactorStatusHeader } from "@/modules/twofa/components/TwoFactorStatusHeader";
import { EmailMethodCard } from "@/modules/twofa/components/methods/EmailMethodCard";
import { SmsMethodCard } from "@/modules/twofa/components/methods/SmsMethodCard";
import { TotpMethodCard } from "@/modules/twofa/components/methods/TotpMethodCard";
import { use2FAStatus, useRemoveTwoFactorMethod, useSetPreferredMethod } from "@/modules/twofa/hooks";
import type { TwoFactorMethod } from "@/modules/twofa/types";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";

// Labels and removal messages from setup page
const METHOD_LABELS: Record<TwoFactorMethod, string> = {
	totp: "Authenticator App",
	email: "Email",
	sms: "SMS",
};

const REMOVAL_CONFIRMATION: Record<TwoFactorMethod, string> = {
	totp: "Removing your authenticator app will unlink it from Tinybeans. Scan a new QR code if you decide to set it up again.",
	sms: "Removing SMS codes will delete your verified phone number. Re-run SMS setup if you want to use text messages again.",
	email:
		"Removing email verification will disable receiving verification codes via email. You can set it up again at any time.",
};

function TwoFactorSettingsPage() {
	const navigate = useNavigate();
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
			setRemovalMessage(result?.message ?? "Method removed successfully.");
			setMethodToRemove(null);
		} catch (err) {
			const apiMessage = (err as { data?: { error?: string } })?.data?.error;
			const fallback =
				err instanceof Error ? err.message : "Failed to remove 2FA method.";
			setRemovalError(apiMessage ?? fallback);
		}
	};

	const handleSetAsDefault = async (method: TwoFactorMethod) => {
		setSwitchError(null);
		setSwitchMessage(null);
		setRemovalError(null);
		setRemovalMessage(null);
		
		try {
			const result = await setPreferredMethod.mutateAsync(method);
			setSwitchMessage(result?.message ?? "Default method updated successfully.");
		} catch (err) {
			const apiMessage = (err as { data?: { error?: string } })?.data?.error;
			const fallback =
				err instanceof Error ? err.message : "Failed to update default method.";
			setSwitchError(apiMessage ?? fallback);
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
				message="Loading 2FA settings..."
				description="We are preparing your two-factor authentication options."
			/>
		);
	}

	// Always show consolidated setup on settings page. If 2FA is not enabled, show an inline callout instead of routing to a separate /2fa/setup page.
	// This ensures there is no dependency on a non-existent setup route.

	if (!status) {
		return (
			<Layout.Error
				title="Two-Factor Authentication"
				description="We couldn't load your 2FA settings. Please try again."
				actionLabel="Retry"
				onAction={() => navigate({ to: "/2fa/settings" })}
			/>
		);
	}

	return (
		<Layout>
			<div className="max-w-3xl mx-auto space-y-6">
				<TwoFactorStatusHeader status={status} />

				<div className="bg-white rounded-lg shadow-md p-6 space-y-6">
					<div className="flex items-start justify-between">
						<div>
							<h2 className="text-xl font-semibold mb-1">
								Setup and Manage Methods
							</h2>
							<p className="text-sm text-gray-600">
								Choose your default method by setting up and configuring
								available options below.
							</p>
						</div>
					</div>

					{!status.is_enabled && (
						<div className="bg-yellow-50 border border-yellow-200 text-yellow-800 text-sm rounded-lg p-4">
							<p className="font-semibold">2FA is not enabled.</p>
							<p>
								Start by setting up a method below. This will also generate
								fresh recovery codes.
							</p>
						</div>
					)}

					{removalMessage && (
						<p className="text-sm text-green-700 bg-green-50 border border-green-200 rounded px-4 py-3">
							{removalMessage}
						</p>
					)}

					{removalError && (
						<p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-4 py-3">
							{removalError}
						</p>
					)}

					{switchMessage && (
						<p className="text-sm text-green-700 bg-green-50 border border-green-200 rounded px-4 py-3">
							{switchMessage}
						</p>
					)}

					{switchError && (
						<p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-4 py-3">
							{switchError}
						</p>
					)}

					<div className="space-y-4">
						<TotpMethodCard
							isCurrent={preferredMethod === "totp"}
							configured={totpConfigured}
							removalInProgress={removalInProgress}
							methodToRemove={methodToRemove}
							onSetup={() => navigate({ to: "/2fa/setup/totp" })}
							onRequestRemoval={() => handleRemovalRequest("totp")}
							onSetAsDefault={() => handleSetAsDefault("totp")}
							setAsDefaultInProgress={switchInProgress}
						/>

						<EmailMethodCard
							isCurrent={preferredMethod === "email"}
							configured={emailConfigured}
							onSetup={() => navigate({ to: "/2fa/setup/email" })}
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
							onSetup={() => navigate({ to: "/2fa/setup/sms" })}
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
						className="text-sm text-gray-600 hover:text-gray-800"
					>
						← Back to home
					</button>
				</div>
			</div>

			<ConfirmDialog
				open={!!methodToRemove}
				onOpenChange={(open) => !open && handleRemovalCancel()}
				title={`Remove ${methodToRemove ? METHOD_LABELS[methodToRemove] : ""}?`}
				description={methodToRemove ? REMOVAL_CONFIRMATION[methodToRemove] : ""}
				confirmLabel="Remove"
				cancelLabel="Cancel"
				variant="destructive"
				isLoading={removalInProgress}
				onConfirm={handleRemovalConfirm}
				onCancel={handleRemovalCancel}
			/>
		</Layout>
	);
}

export const Route = createFileRoute("/2fa/settings")({
	component: TwoFactorSettingsPage,
});
