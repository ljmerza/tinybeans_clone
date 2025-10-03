/**
 * 2FA Settings Page
 * Manage 2FA configuration, recovery codes, and trusted devices
 */

import { ButtonGroup, Layout, StatusMessage } from "@/components";
import { Button } from "@/components/ui/button";
import { verificationCodeSchema } from "@/lib/validations";
import { RecoveryCodeList } from "@/modules/twofa/components/RecoveryCodeList";
import { VerificationInput } from "@/modules/twofa/components/VerificationInput";
import { EmailMethodCard } from "@/modules/twofa/components/methods/EmailMethodCard";
import { SmsMethodCard } from "@/modules/twofa/components/methods/SmsMethodCard";
import { TotpMethodCard } from "@/modules/twofa/components/methods/TotpMethodCard";
import {
	use2FAStatus,
	useDisable2FA,
	useGenerateRecoveryCodes,
	useRemoveTwoFactorMethod,
} from "@/modules/twofa/hooks";
import type { TwoFactorMethod, TwoFactorStatusResponse } from "@/modules/twofa/types";
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



function TwoFactorStatusHeader({ status }: { status: TwoFactorStatusResponse }) {
	return (
		<div className="bg-white rounded-lg shadow-md p-6">
			<div className="flex items-start justify-between">
				<div>
					<h1 className="text-2xl font-semibold mb-2">Two-Factor Authentication</h1>
					<div className="flex items-center gap-2">
						{status.is_enabled ? (
							<>
								<span className="inline-flex items-center bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm font-semibold">
									✓ Enabled
								</span>
								<span className="text-sm text-gray-600">
									Method:{" "}
									<span className="font-semibold">
										{status.preferred_method?.toUpperCase()}
									</span>
								</span>
							</>
						) : (
							<span className="inline-flex items-center bg-yellow-100 text-yellow-800 px-3 py-1 rounded-full text-sm font-semibold">
								⚠️ Not enabled
							</span>
						)}
					</div>
				</div>
			</div>
		</div>
	);
}

// Removed old PreferredMethodSection in favor of consolidated method cards

interface RecoveryCodesSectionProps {
	showNewCodes: boolean;
	isGenerating: boolean;
	errMessage?: string;
	codes?: string[];
	onGenerate: () => void;
	onViewCurrent: () => void;
	onHideCodes: () => void;
}

function RecoveryCodesSection({
	showNewCodes,
	isGenerating,
	errMessage,
	codes,
	onGenerate,
	onViewCurrent,
	onHideCodes,
}: RecoveryCodesSectionProps) {
	return (
		<div className="bg-white rounded-lg shadow-md p-6">
			<h2 className="text-xl font-semibold mb-4">Recovery Codes</h2>

			{!showNewCodes ? (
				<div className="space-y-4">
					<p className="text-gray-600 text-sm">
						Recovery codes can be used to access your account if you lose access to your authenticator device. Each code can only be used once.
					</p>

					<div className="flex gap-2">
						<Button onClick={onGenerate} disabled={isGenerating} variant="outline">
							{isGenerating ? "Generating..." : "Generate New Recovery Codes"}
						</Button>

						<Button onClick={onViewCurrent} variant="outline">
							View Current Codes
						</Button>
					</div>

					{errMessage && (
						<StatusMessage variant="error">{errMessage}</StatusMessage>
					)}
				</div>
			) : (
				<div className="space-y-4">
					{codes && <RecoveryCodeList codes={codes} />}
					<Button onClick={onHideCodes} variant="outline">
						Done
					</Button>
				</div>
			)}
		</div>
	);
}

function TrustedDevicesSection({ onManage }: { onManage: () => void }) {
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

interface DisableTwoFactorSectionProps {
	showDisableConfirm: boolean;
	canDisable: boolean;
	disableCode: string;
	isDisabling: boolean;
	errMessage?: string;
	onRequestDisable: () => void;
	onCancelDisable: () => void;
	onCodeChange: (value: string) => void;
	onConfirmDisable: () => void;
}

function DisableTwoFactorSection({
	showDisableConfirm,
	canDisable,
	disableCode,
	isDisabling,
	errMessage,
	onRequestDisable,
	onCancelDisable,
	onCodeChange,
	onConfirmDisable,
}: DisableTwoFactorSectionProps) {
	return (
		<div className="bg-white rounded-lg shadow-md p-6">
			<h2 className="text-xl font-semibold mb-4 text-red-600">
				Disable Two-Factor Authentication
			</h2>

			{!showDisableConfirm ? (
				<div className="space-y-4">
					<p className="text-gray-600 text-sm">
						Disabling 2FA will make your account less secure. You'll only need your password to log in.
					</p>
					<Button
						onClick={onRequestDisable}
						variant="outline"
						className="text-red-600 border-red-300 hover:bg-red-50"
					>
						Disable 2FA
					</Button>
				</div>
			) : (
				<div className="space-y-4">
					<div className="bg-red-50 border border-red-200 rounded p-4">
						<p className="text-sm text-red-800 font-semibold mb-2">⚠️ Are you sure?</p>
						<p className="text-sm text-red-800">
							Enter your 6-digit verification code to confirm disabling 2FA.
						</p>
					</div>

					<VerificationInput
						value={disableCode}
						onChange={onCodeChange}
						onComplete={onConfirmDisable}
						disabled={isDisabling}
					/>

					<div className="flex gap-2">
						<Button
							onClick={onConfirmDisable}
							disabled={!canDisable || isDisabling}
							variant="outline"
							className="flex-1 text-red-600 border-red-300 hover:bg-red-50"
						>
							{isDisabling ? "Disabling..." : "Confirm Disable"}
						</Button>
						<Button
							onClick={onCancelDisable}
							variant="outline"
							className="flex-1"
							disabled={isDisabling}
						>
							Cancel
						</Button>
					</div>

					{errMessage && (
						<StatusMessage variant="error" align="center">{errMessage}</StatusMessage>
					)}
				</div>
			)}
		</div>
	);
}

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
