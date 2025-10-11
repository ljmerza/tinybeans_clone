/**
 * 2FA Setup Page
 * Choose and configure 2FA method
 */

import { ButtonGroup, Layout } from "@/components";
import { requireAuth } from "@/features/auth";
import { Button } from "@/components/ui/button";
import { extractApiError } from "@/features/auth/utils";
import {
	EmailMethodCard,
	SmsMethodCard,
	TotpMethodCard,
	twoFaKeys,
	twoFactorApi,
	use2FAStatus,
	useRemoveTwoFactorMethod,
} from "@/features/twofa";
import type { TwoFactorMethod } from "@/features/twofa";
import type { QueryClient } from "@tanstack/react-query";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";

const METHOD_LABELS: Record<TwoFactorMethod, string> = {
	totp: "Authenticator App",
	email: "Email",
	sms: "SMS",
};

type RemovableMethod = Exclude<TwoFactorMethod, "email">;

const REMOVAL_CONFIRMATION: Record<RemovableMethod, string> = {
	totp: "Removing your authenticator app will unlink it from Tinybeans. Scan a new QR code if you decide to set it up again.",
	sms: "Removing SMS codes will delete your verified phone number. Re-run SMS setup if you want to use text messages again.",
};

function TwoFactorSetupPage() {
	const navigate = useNavigate();
	const { data: status, isLoading, error } = use2FAStatus();
	const removeMethod = useRemoveTwoFactorMethod();

	const [methodToRemove, setMethodToRemove] = useState<RemovableMethod | null>(
		null,
	);
	const [removalMessage, setRemovalMessage] = useState<string | null>(null);
	const [removalError, setRemovalError] = useState<string | null>(null);

	const currentMethod = status?.preferred_method ?? null;
	const totpConfigured = Boolean(status?.has_totp);
	const smsConfigured = Boolean(status?.has_sms);
	const emailConfigured = Boolean(status?.has_email);
	const emailAddress =
		status?.email_address ?? status?.backup_email ?? undefined;
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
				result?.message ??
					`${METHOD_LABELS[methodToRemove]} removed successfully.`,
			);
			setMethodToRemove(null);
		} catch (err) {
			setRemovalError(extractApiError(err, "Failed to remove 2FA method."));
		}
	};

	if (isLoading) {
		return (
			<Layout.Loading
				message="Loading 2FA settings..."
				description="We are fetching your current two-factor authentication configuration."
			/>
		);
	}

	if (error) {
		return (
			<Layout.Error
				title="Failed to load 2FA settings"
				message={error instanceof Error ? error.message : undefined}
				description="Try again in a moment or return home to continue navigating."
				actionLabel="Go Home"
				onAction={() => navigate({ to: "/" })}
			/>
		);
	}

	return (
		<Layout>
			<div className="max-w-2xl mx-auto">
				<div className="bg-white rounded-lg shadow-md p-6 space-y-6">
					<div className="text-center space-y-2">
						<h1 className="text-3xl font-bold">
							Enable Two-Factor Authentication
						</h1>
						<p className="text-gray-600">
							Add an extra layer of security to your account.
						</p>
					</div>

					{status?.is_enabled && (
						<div className="bg-yellow-50 border border-yellow-200 text-yellow-800 text-sm rounded-lg p-4">
							<p className="font-semibold">2FA is already enabled.</p>
							<p>
								Starting a new setup will update your default 2FA method and
								refresh your recovery codes.
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

					{methodToRemove && (
						<div className="border border-red-200 bg-red-50 rounded-md p-4 space-y-3">
							<p className="text-sm text-red-800 font-semibold">
								Confirm removal of {METHOD_LABELS[methodToRemove]}?
							</p>
							<p className="text-xs text-red-700">
								{REMOVAL_CONFIRMATION[methodToRemove]}
							</p>
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
							isCurrent={currentMethod === "totp"}
							configured={totpConfigured}
							removalInProgress={removalInProgress}
							methodToRemove={methodToRemove}
							onSetup={() => navigate({ to: "/profile/2fa/setup/totp" })}
							onRequestRemoval={() => handleRemovalRequest("totp")}
						/>

						<EmailMethodCard
							isCurrent={currentMethod === "email"}
							configured={emailConfigured}
							emailAddress={emailAddress}
							onSetup={() => navigate({ to: "/profile/2fa/setup/email" })}
						/>

						<SmsMethodCard
							isCurrent={currentMethod === "sms"}
							configured={smsConfigured}
							phoneNumber={status?.phone_number}
							removalInProgress={removalInProgress}
							methodToRemove={methodToRemove}
							onSetup={() => navigate({ to: "/profile/2fa/setup/sms" })}
							onRequestRemoval={() => handleRemovalRequest("sms")}
						/>
					</div>

					<div className="pt-4 border-t text-center">
						<Button variant="ghost" onClick={() => navigate({ to: "/" })}>
							Skip for now
						</Button>
					</div>
				</div>
			</div>
		</Layout>
	);
}

export const Route = createFileRoute("/profile/2fa/setup/")({
	beforeLoad: requireAuth,
	loader: ({ context }) => {
		const { queryClient } = context as { queryClient: QueryClient };
		return queryClient.ensureQueryData({
			queryKey: twoFaKeys.status(),
			queryFn: () => twoFactorApi.getStatus(),
		});
	},
	component: TwoFactorSetupPage,
});
