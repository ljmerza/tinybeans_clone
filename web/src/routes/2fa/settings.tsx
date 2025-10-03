/**
 * 2FA Settings Page
 * Manage 2FA configuration, recovery codes, and trusted devices
 */

import { ButtonGroup, Layout } from "@/components";
import { Button } from "@/components/ui/button";
import { verificationCodeSchema } from "@/lib/validations";
import { DisableTwoFactorSection } from "@/modules/twofa/components/DisableTwoFactorSection";
import { RecoveryCodesSection } from "@/modules/twofa/components/RecoveryCodesSection";
import { TrustedDevicesSection } from "@/modules/twofa/components/TrustedDevicesSection";
import { TwoFactorStatusHeader } from "@/modules/twofa/components/TwoFactorStatusHeader";
import { EmailMethodCard } from "@/modules/twofa/components/methods/EmailMethodCard";
import { SmsMethodCard } from "@/modules/twofa/components/methods/SmsMethodCard";
import { TotpMethodCard } from "@/modules/twofa/components/methods/TotpMethodCard";
import {
	use2FAStatus,
	useDisable2FA,
	useGenerateRecoveryCodes,
	useRemoveTwoFactorMethod,
} from "@/modules/twofa/hooks";
import type { TwoFactorMethod } from "@/modules/twofa/types";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";

// Labels and removal messages from setup page
const METHOD_LABELS: Record<TwoFactorMethod, string> = {
	"totp": "Authenticator App",
	"email": "Email",
	"sms": "SMS",
};

type RemovableMethod = Exclude<TwoFactorMethod, "email">;
const REMOVAL_CONFIRMATION: Record<RemovableMethod, string> = {
	"totp":
		"Removing your authenticator app will unlink it from Tinybeans. Scan a new QR code if you decide to set it up again.",
	"sms":
		"Removing SMS codes will delete your verified phone number. Re-run SMS setup if you want to use text messages again.",
};

function TwoFactorSettingsPage() {
	const navigate = useNavigate();
	const { data: status, isLoading } = use2FAStatus();
	const disable2FA = useDisable2FA();
	const generateCodes = useGenerateRecoveryCodes();
	const removeMethod = useRemoveTwoFactorMethod();

	const [showDisableConfirm, setShowDisableConfirm] = useState(false);
	const [disableCode, setDisableCode] = useState("");
	const [showNewCodes, setShowNewCodes] = useState(false);
	const [methodToRemove, setMethodToRemove] = useState<TwoFactorMethod | null>(null);
	const [removalMessage, setRemovalMessage] = useState<string | null>(null);
	const [removalError, setRemovalError] = useState<string | null>(null);

	const handleDisable = async () => {
		const validation = verificationCodeSchema.safeParse(disableCode);
		if (!validation.success) return;

		try {
			await disable2FA.mutateAsync(disableCode);
			navigate({ to: "/" });
		} catch (error) {
			setDisableCode("");
		}
	};

	const handleGenerateNewCodes = async () => {
		try {
			await generateCodes.mutateAsync();
			setShowNewCodes(true);
		} catch (error) {
			console.error("Failed to generate codes:", error);
		}
	};

	const removalInProgress = removeMethod.isPending;
	const handleRemovalRequest = (method: Exclude<TwoFactorMethod, "email">) => {
		setRemovalError(null);
		setRemovalMessage(null);
		setMethodToRemove(method);
	};
	const handleRemovalCancel = () => {
		if (!removalInProgress) {
			setMethodToRemove(null);
		}
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
			const fallback = err instanceof Error ? err.message : "Failed to remove 2FA method.";
			setRemovalError(apiMessage ?? fallback);
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

	const canDisable = verificationCodeSchema.safeParse(disableCode).success;

	return (
		<Layout>
			<div className="max-w-3xl mx-auto space-y-6">
				<TwoFactorStatusHeader status={status} />

				<div className="bg-white rounded-lg shadow-md p-6 space-y-6">
					<div className="flex items-start justify-between">
						<div>
							<h2 className="text-xl font-semibold mb-1">Setup and Manage Methods</h2>
							<p className="text-sm text-gray-600">
								Choose your default method by setting up and configuring available options below.
							</p>
						</div>
					</div>

					{!status.is_enabled && (
						<div className="bg-yellow-50 border border-yellow-200 text-yellow-800 text-sm rounded-lg p-4">
							<p className="font-semibold">2FA is not enabled.</p>
							<p>Start by setting up a method below. This will also generate fresh recovery codes.</p>
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

					{methodToRemove && (
						<div className="border border-red-200 bg-red-50 rounded-md p-4 space-y-3">
							<p className="text-sm text-red-800 font-semibold">
								Confirm removal of {METHOD_LABELS[methodToRemove]}?
							</p>
							<p className="text-xs text-red-700">{REMOVAL_CONFIRMATION[methodToRemove as Exclude<TwoFactorMethod, "email">]}</p>
							<ButtonGroup className="flex-col sm:flex-row">
								<Button
									onClick={handleRemovalConfirm}
									disabled={removalInProgress}
									className="sm:flex-1 bg-red-600 hover:bg-red-700 text-white"
								>
									{removalInProgress ? "Removing..." : "Confirm removal"}
								</Button>
								<Button
									variant="outline"
									onClick={handleRemovalCancel}
									disabled={removalInProgress}
									className="sm:flex-1"
								>
									Cancel
								</Button>
							</ButtonGroup>
						</div>
					)}

					<div className="space-y-4">
						<TotpMethodCard
							isCurrent={preferredMethod === "totp"}
							configured={totpConfigured}
							removalInProgress={removalInProgress}
							methodToRemove={methodToRemove}
							onSetup={() => navigate({ to: "/2fa/setup/totp" })}
							onRequestRemoval={() => handleRemovalRequest("totp")}
						/>

						<EmailMethodCard
							isCurrent={preferredMethod === "email"}
							configured={emailConfigured}
							onSetup={() => navigate({ to: "/2fa/setup/email" })}
						/>

						<SmsMethodCard
							isCurrent={preferredMethod === "sms"}
							configured={smsConfigured}
							phoneNumber={phoneNumber}
							removalInProgress={removalInProgress}
							methodToRemove={methodToRemove}
							onSetup={() => navigate({ to: "/2fa/setup/sms" })}
							onRequestRemoval={() => handleRemovalRequest("sms")}
						/>
					</div>
				</div>

				<RecoveryCodesSection
					showNewCodes={showNewCodes}
					isGenerating={generateCodes.isPending}
					errMessage={generateCodes.error?.message}
					codes={generateCodes.data?.recovery_codes}
					onGenerate={handleGenerateNewCodes}
					onViewCurrent={() => navigate({ to: "/2fa/settings" })}
					onHideCodes={() => setShowNewCodes(false)}
				/>

				<TrustedDevicesSection onManage={() => navigate({ to: "/2fa/trusted-devices" })} />

				<DisableTwoFactorSection
					showDisableConfirm={showDisableConfirm}
					canDisable={canDisable}
					disableCode={disableCode}
					isDisabling={disable2FA.isPending}
					errMessage={disable2FA.error?.message}
					onRequestDisable={() => setShowDisableConfirm(true)}
					onCancelDisable={() => {
						setShowDisableConfirm(false);
						setDisableCode("");
					}}
					onCodeChange={setDisableCode}
					onConfirmDisable={handleDisable}
				/>

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
		</Layout>
	);
}

export const Route = createFileRoute("/2fa/settings")({
	component: TwoFactorSettingsPage,
});
