/**
 * 2FA Settings Page
 * Manage 2FA configuration, recovery codes, and trusted devices
 */

import { Layout, StatusMessage } from "@/components";
import { Button } from "@/components/ui/button";
import { verificationCodeSchema } from "@/lib/validations";
import { RecoveryCodeList } from "@/modules/twofa/components/RecoveryCodeList";
import { VerificationInput } from "@/modules/twofa/components/VerificationInput";
import {
	use2FAStatus,
	useDisable2FA,
	useGenerateRecoveryCodes,
	useSetPreferredMethod,
} from "@/modules/twofa/hooks";
import type {
	TwoFactorMethod,
	TwoFactorStatusResponse,
} from "@/modules/twofa/types";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";

interface MethodOption {
	key: TwoFactorMethod;
	title: string;
	description: string;
	available: boolean;
	helper?: string;
}

function TwoFactorStatusHeader({ status }: { status: TwoFactorStatusResponse }) {
	return (
		<div className="bg-white rounded-lg shadow-md p-6">
			<div className="flex items-start justify-between">
				<div>
					<h1 className="text-2xl font-semibold mb-2">Two-Factor Authentication</h1>
					<div className="flex items-center gap-2">
						<span className="inline-flex items-center bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm font-semibold">
							✓ Enabled
						</span>
						<span className="text-sm text-gray-600">
							Method:{" "}
							<span className="font-semibold">
								{status.preferred_method?.toUpperCase()}
							</span>
						</span>
					</div>
				</div>
			</div>
		</div>
	);
}

interface PreferredMethodSectionProps {
	methodOptions: MethodOption[];
	preferredMethod: TwoFactorMethod | null;
	pendingMethod: TwoFactorMethod | null;
	isUpdating: boolean;
	errorMessage?: string;
	phoneNumber?: string;
	onSetPreferred: (method: TwoFactorMethod) => void;
	onConfigure: () => void;
}

function PreferredMethodSection({
	methodOptions,
	preferredMethod,
	pendingMethod,
	isUpdating,
	errorMessage,
	phoneNumber,
	onSetPreferred,
	onConfigure,
}: PreferredMethodSectionProps) {
	return (
		<div className="bg-white rounded-lg shadow-md p-6 space-y-4">
			<div className="flex items-start justify-between">
				<div>
					<h2 className="text-xl font-semibold mb-1">Default Verification Method</h2>
					<p className="text-sm text-gray-600">
						Choose which factor we request during login. Configure additional factors from the setup page whenever you need to switch.
					</p>
				</div>
				{isUpdating && <span className="text-sm text-gray-500">Updating…</span>}
			</div>

			<div className="grid gap-4 md:grid-cols-3">
				{methodOptions.map((option) => {
					const isDefault = preferredMethod === option.key;
					const isPendingOption = isUpdating && pendingMethod === option.key;

					return (
						<div
							key={option.key}
							className="border border-gray-200 rounded-lg p-4 flex flex-col gap-3"
						>
							<div className="flex items-center justify-between">
								<h3 className="font-semibold text-lg">{option.title}</h3>
								{isDefault && (
									<span className="bg-green-100 text-green-700 text-xs font-semibold px-2 py-1 rounded-full">
										Default
									</span>
								)}
							</div>
							<p className="text-sm text-gray-600">{option.description}</p>

							{option.key === "sms" && phoneNumber && (
								<p className="text-sm text-gray-500">Sending to {phoneNumber}</p>
							)}

							{option.helper && (
								<p className="text-xs text-gray-500">{option.helper}</p>
							)}

							<div className="mt-auto">
								{option.available ? (
									isDefault ? (
										<p className="text-sm text-green-700 font-medium">Currently in use</p>
									) : (
										<Button
											onClick={() => onSetPreferred(option.key)}
											disabled={isUpdating}
											className="w-full"
										>
											{isPendingOption ? "Saving…" : "Set as default"}
										</Button>
									)
								) : (
									<Button
										variant="outline"
										onClick={onConfigure}
										className="w-full"
									>
										{option.key === "sms" && phoneNumber
											? "Verify phone number"
											: "Configure in setup"}
									</Button>
								)}
							</div>
						</div>
					);
				})}
			</div>

			{errorMessage && (
				<StatusMessage variant="error">{errorMessage}</StatusMessage>
			)}
		</div>
	);
}

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
	const setPreferredMethod = useSetPreferredMethod();

	const [showDisableConfirm, setShowDisableConfirm] = useState(false);
	const [disableCode, setDisableCode] = useState("");
	const [showNewCodes, setShowNewCodes] = useState(false);
	const [pendingMethod, setPendingMethod] = useState<TwoFactorMethod | null>(null);

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

	const handleSetPreferred = (method: TwoFactorMethod) => {
		setPendingMethod(method);
		setPreferredMethod.mutate(method, {
			onSettled: () => setPendingMethod(null),
		});
	};

	const preferredMethod = status?.preferred_method ?? null;
	const smsVerified = Boolean(status?.sms_verified);
	const methodOptions: Array<{
		key: TwoFactorMethod;
		title: string;
		description: string;
		available: boolean;
		helper?: string;
	}> = [
		{
			key: "totp",
			title: "Authenticator App",
			description:
				"Use 6-digit codes generated by apps like Google Authenticator, 1Password, or Authy.",
			available: Boolean(status?.has_totp),
			helper: "Scan the QR code via the setup page if you need to reconfigure your authenticator app.",
		},
		{
			key: "email",
			title: "Email",
			description: "Receive verification codes at your account email address.",
			available: true,
			helper: "Email is always available as a fallback option.",
		},
		{
			key: "sms",
			title: "SMS",
			description: "Get verification codes sent to your mobile phone via text message.",
			available: smsVerified,
			helper: status?.phone_number
				? smsVerified
					? `Verified number: ${status.phone_number}`
					: `Number pending verification: ${status.phone_number}`
				: "Add a phone number from the setup page to enable SMS.",
		},
	];

	if (isLoading) {
		return (
			<Layout.Loading
				message="Loading 2FA settings..."
				description="We are preparing your two-factor authentication options."
			/>
		);
	}

	if (!status?.is_enabled) {
		return (
			<Layout.Error
				title="Two-Factor Authentication"
				description="2FA is not enabled for your account. Enable it to add another layer of security."
				actionLabel="Enable 2FA"
				onAction={() => navigate({ to: "/2fa/setup" })}
			/>
		);
	}

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
	const phoneNumber = status.phone_number;

	return (
		<Layout>
			<div className="max-w-3xl mx-auto space-y-6">
				<TwoFactorStatusHeader status={status} />

				<PreferredMethodSection
					methodOptions={methodOptions}
					preferredMethod={preferredMethod}
					pendingMethod={pendingMethod}
					isUpdating={setPreferredMethod.isPending}
					errorMessage={setPreferredMethod.error?.message}
					phoneNumber={phoneNumber}
					onSetPreferred={handleSetPreferred}
					onConfigure={() => navigate({ to: "/2fa/setup" })}
				/>

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
