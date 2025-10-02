/**
 * 2FA Setup Page
 * Choose and configure 2FA method
 */

import { Layout } from "@/components/Layout";
import { LoadingPage } from "@/components/LoadingSpinner";
import { Button } from "@/components/ui/button";
import { EmailSetup } from "@/modules/twofa/components/EmailSetup";
import { SmsSetup } from "@/modules/twofa/components/SmsSetup";
import { TotpSetup } from "@/modules/twofa/components/TotpSetup";
import { use2FAStatus, useRemoveTwoFactorMethod } from "@/modules/twofa/hooks";
import type { TwoFactorMethod } from "@/modules/twofa/types";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useMemo, useState } from "react";


const METHOD_LABELS: Record<TwoFactorMethod, string> = {
	totp: "Authenticator App",
	email: "Email",
	sms: "SMS",
};

type RemovableMethod = Exclude<TwoFactorMethod, "email">;

const REMOVAL_CONFIRMATION: Record<RemovableMethod, string> = {
	totp:
		"Removing your authenticator app will unlink it from Tinybeans. Scan a new QR code if you decide to set it up again.",
	sms:
		"Removing SMS codes will delete your verified phone number. Re-run SMS setup if you want to use text messages again.",
};

function TwoFactorSetupPage() {
	const navigate = useNavigate();
	const [selectedMethod, setSelectedMethod] = useState<TwoFactorMethod | null>(
		null,
	);

	const { data: status, isLoading, error } = use2FAStatus();
	const removeMethod = useRemoveTwoFactorMethod();
	const [methodToRemove, setMethodToRemove] = useState<
		RemovableMethod | null
	>(null);
	const [removalMessage, setRemovalMessage] = useState<string | null>(null);
	const [removalError, setRemovalError] = useState<string | null>(null);
	const currentMethod = useMemo(
		() => status?.preferred_method ?? null,
		[status?.preferred_method],
	);
	const defaultSmsPhone = status?.phone_number ?? "";
	const totpConfigured = Boolean(status?.has_totp);
	const smsConfigured = Boolean(status?.has_sms);
	const configuredMethods = useMemo(
		() => {
			const methods: Array<{
				key: RemovableMethod;
				description: string;
				detail?: string;
			}> = [];

			if (totpConfigured) {
				methods.push({
					key: "totp",
					description:
						"Codes from your authenticator app will stop working after removal.",
				});
			}

			if (smsConfigured) {
				methods.push({
					key: "sms",
					description: "We will no longer send verification codes via text message.",
					detail: status?.phone_number
						? `Currently sending to ${status.phone_number}`
						: undefined,
				});
			}

			return methods;
		},
		[totpConfigured, smsConfigured, status?.phone_number],
	);
	const removalInProgress = removeMethod.isPending;
	const handleRemovalRequest = (method: RemovableMethod) => {
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
		if (!methodToRemove) {
			return;
		}
		setRemovalError(null);
		try {
			const result = await removeMethod.mutateAsync(methodToRemove);
			setRemovalMessage(
				result?.message ?? `${METHOD_LABELS[methodToRemove]} removed successfully.`,
			);
			setMethodToRemove(null);
		} catch (error) {
			const apiMessage = (error as any)?.data?.error;
			const fallback =
				error instanceof Error ? error.message : "Failed to remove 2FA method.";
			setRemovalError(apiMessage ?? fallback);
		}
	};

	const handleComplete = () => {
		navigate({ to: "/2fa/settings" });
	};

	const handleCancel = () => {
		setSelectedMethod(null);
	};

	if (isLoading) {
		return (
			<Layout>
				<LoadingPage
					message="Loading 2FA settings..."
					fullScreen={false}
				/>
			</Layout>
		);
	}

	if (error) {
		return (
			<Layout>
				<div className="flex justify-center py-16">
					<div className="max-w-md w-full bg-white rounded-lg shadow-md p-6 text-center">
						<p className="text-red-600">Failed to load 2FA settings</p>
						<Button onClick={() => navigate({ to: "/" })} className="mt-4">
							Go Home
						</Button>
					</div>
				</div>
			</Layout>
		);
	}

	return (
		<Layout>
			<div className="max-w-2xl mx-auto">
				<div className="bg-white rounded-lg shadow-md p-6">
				{!selectedMethod ? (
					<div className="space-y-6">
						<div className="text-center">
							<h1 className="text-3xl font-bold mb-2">
								Enable Two-Factor Authentication
							</h1>
							<p className="text-gray-600">
								Add an extra layer of security to your account
							</p>
						</div>

						{status?.is_enabled && (
							<div className="bg-yellow-50 border border-yellow-200 text-yellow-800 text-sm rounded-lg p-4">
								<p className="font-semibold">2FA is already enabled.</p>
								<p>
									Starting a new setup will update your default 2FA method and refresh your recovery codes.
								</p>
							</div>
						)}

						{configuredMethods.length > 0 && (
							<div className="space-y-3 border border-gray-200 bg-gray-50 rounded-lg p-4">
								<div className="space-y-1">
									<h2 className="text-lg font-semibold">Remove a configured method</h2>
									<p className="text-sm text-gray-600">
										Remove a method you no longer use. We'll ask you to confirm before anything changes.
									</p>
								</div>

								{removalMessage && (
									<p className="text-sm text-green-700 bg-white border border-green-200 rounded px-3 py-2">
										{removalMessage}
									</p>
								)}

								{removalError && (
									<p className="text-sm text-red-600 bg-white border border-red-200 rounded px-3 py-2">
										{removalError}
									</p>
								)}

								<div className="space-y-3">
									{configuredMethods.map(({ key, description, detail }) => (
										<div
											key={key}
											className="border border-gray-200 bg-white rounded-md p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3"
										>
											<div>
												<p className="font-medium text-gray-900">
													{METHOD_LABELS[key]}
												</p>
												<p className="text-sm text-gray-600">{description}</p>
												{detail && (
													<p className="text-xs text-gray-500 mt-1">{detail}</p>
												)}
											</div>
											<Button
												variant="outline"
												onClick={() => handleRemovalRequest(key)}
												disabled={removalInProgress}
												className="sm:w-auto border-red-200 text-red-600 hover:bg-red-50"
											>
												{removalInProgress && methodToRemove === key
													? "Removing..."
													: "Remove"}
											</Button>
										</div>
									))}
								</div>

								{methodToRemove && (
									<div className="border border-red-200 bg-red-50 rounded-md p-4 space-y-3">
										<p className="text-sm text-red-800 font-semibold">
											Confirm removal of {METHOD_LABELS[methodToRemove]}?
										</p>
										<p className="text-xs text-red-700">
											{REMOVAL_CONFIRMATION[methodToRemove]}
										</p>
										<div className="flex flex-col sm:flex-row gap-2">
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
										</div>
									</div>
								)}
							</div>
						)}

						<div className="space-y-4">
									{/* TOTP Method */}
									<button
										type="button"
										disabled={totpConfigured}
										onClick={() => setSelectedMethod("totp")}
										className="w-full p-6 border-2 border-gray-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-all text-left group disabled:opacity-60 disabled:cursor-not-allowed disabled:hover:border-gray-200 disabled:hover:bg-white"
									>
									<div className="flex items-start gap-4">
										<div className="text-3xl">📱</div>
										<div className="flex-1">
											<h3 className="text-lg font-semibold mb-1 group-hover:text-blue-600">
												Authenticator App (Recommended)
											</h3>
											<p className="text-sm text-gray-600 mb-2">
												Use Google Authenticator, Authy, 1Password, or similar
												apps to generate verification codes
											</p>
											<div className="flex flex-wrap gap-2 text-xs">
												<span className="bg-green-100 text-green-800 px-2 py-1 rounded">
													Most Secure
												</span>
												<span className="bg-blue-100 text-blue-800 px-2 py-1 rounded">
													Works Offline
												</span>
												<span className="bg-purple-100 text-purple-800 px-2 py-1 rounded">
													No Costs
												</span>
											</div>

											{currentMethod === "totp" && (
												<p className="text-xs font-semibold text-green-700 mt-3">
													Current default method
												</p>
											)}
											{totpConfigured && (
												<p className="text-xs text-gray-500 mt-2">
													Remove this method above before setting up the authenticator again.
												</p>
											)}
										</div>
										</div>
									</button>

								{/* Email Method */}
								<button
									onClick={() => setSelectedMethod("email")}
									className="w-full p-6 border-2 border-gray-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-all text-left group"
								>
									<div className="flex items-start gap-4">
										<div className="text-3xl">📧</div>
										<div className="flex-1">
											<h3 className="text-lg font-semibold mb-1 group-hover:text-blue-600">
												Email Verification
											</h3>
											<p className="text-sm text-gray-600 mb-2">
												Receive verification codes via email
											</p>
											<div className="flex flex-wrap gap-2 text-xs">
												<span className="bg-blue-100 text-blue-800 px-2 py-1 rounded">
													Simple
												</span>
												<span className="bg-purple-100 text-purple-800 px-2 py-1 rounded">
													No Extra App Needed
												</span>
											</div>

											{currentMethod === "email" && (
												<p className="text-xs font-semibold text-green-700 mt-3">
													Current default method
												</p>
											)}
										</div>
									</div>
								</button>

									{/* SMS Method */}
									<button
										type="button"
										disabled={smsConfigured}
										onClick={() => setSelectedMethod("sms")}
										className="w-full p-6 border-2 border-gray-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-all text-left group disabled:opacity-60 disabled:cursor-not-allowed disabled:hover:border-gray-200 disabled:hover:bg-white"
									>
									<div className="flex items-start gap-4">
										<div className="text-3xl">💬</div>
										<div className="flex-1">
											<h3 className="text-lg font-semibold mb-1 group-hover:text-blue-600">
												SMS Verification
											</h3>
											<p className="text-sm text-gray-600 mb-2">
												Receive verification codes via text message
											</p>
											<div className="flex flex-wrap gap-2 text-xs">
												<span className="bg-blue-100 text-blue-800 px-2 py-1 rounded">
													Quick
												</span>
												<span className="bg-orange-100 text-orange-800 px-2 py-1 rounded">
													Requires Phone Number
												</span>
											</div>

											{currentMethod === "sms" && (
												<p className="text-xs font-semibold text-green-700 mt-3">
													Current default method
												</p>
											)}
											{smsConfigured && (
												<p className="text-xs text-gray-500 mt-2">
													Remove this method above before setting up SMS again.
												</p>
											)}
										</div>
										</div>
									</button>
							</div>

							<div className="pt-4 border-t text-center">
								<button
									onClick={() => navigate({ to: "/" })}
									className="text-sm text-gray-600 hover:text-gray-800"
								>
									Skip for now
								</button>
							</div>
						</div>
					) : (
						<div>
							{selectedMethod === "totp" && (
								<TotpSetup
									onComplete={handleComplete}
									onCancel={handleCancel}
								/>
							)}
							{selectedMethod === "email" && (
								<EmailSetup onComplete={handleComplete} onCancel={handleCancel} />
							)}
							{selectedMethod === "sms" && (
								<SmsSetup
									defaultPhone={defaultSmsPhone}
									onComplete={handleComplete}
									onCancel={handleCancel}
								/>
							)}
						</div>
					)}
				</div>
			</div>
		</Layout>
	);
}

export const Route = createFileRoute("/2fa/setup")({
	component: TwoFactorSetupPage,
});
