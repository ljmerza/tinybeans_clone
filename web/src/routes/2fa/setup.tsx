/**
 * 2FA Setup Page
 * Choose and configure 2FA method
 */

import { LoadingPage } from "@/components/LoadingSpinner";
import { Button } from "@/components/ui/button";
import { TotpSetup } from "@/modules/twofa/components/TotpSetup";
import { use2FAStatus } from "@/modules/twofa/hooks";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";

function TwoFactorSetupPage() {
	const navigate = useNavigate();
	const [selectedMethod, setSelectedMethod] = useState<
		"totp" | "email" | "sms" | null
	>(null);

	const { data: status, isLoading, error } = use2FAStatus();

	// If 2FA already enabled, redirect to settings
	useEffect(() => {
		if (status?.is_enabled) {
			navigate({ to: "/2fa/settings" });
		}
	}, [status, navigate]);

	const handleComplete = () => {
		navigate({ to: "/2fa/settings" });
	};

	const handleCancel = () => {
		setSelectedMethod(null);
	};

	if (isLoading) {
		return <LoadingPage message="Loading 2FA settings..." />;
	}

	if (error) {
		return (
			<div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
				<div className="max-w-md w-full bg-white rounded-lg shadow-md p-6 text-center">
					<p className="text-red-600">Failed to load 2FA settings</p>
					<Button onClick={() => navigate({ to: "/" })} className="mt-4">
						Go Home
					</Button>
				</div>
			</div>
		);
	}

	// Prevent rendering if already enabled (navigation is in progress)
	if (status?.is_enabled) {
		return null;
	}

	return (
		<div className="min-h-screen bg-gray-50 py-12 px-4">
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

							<div className="space-y-4">
								{/* TOTP Method */}
								<button
									onClick={() => setSelectedMethod("totp")}
									className="w-full p-6 border-2 border-gray-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-all text-left group"
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
										</div>
									</div>
								</button>

								{/* SMS Method */}
								<button
									onClick={() => setSelectedMethod("sms")}
									className="w-full p-6 border-2 border-gray-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-all text-left group"
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
								<div className="text-center py-8">
									<p className="text-gray-600">
										Email 2FA setup coming soon...
									</p>
									<Button onClick={handleCancel} className="mt-4">
										Back
									</Button>
								</div>
							)}
							{selectedMethod === "sms" && (
								<div className="text-center py-8">
									<p className="text-gray-600">SMS 2FA setup coming soon...</p>
									<Button onClick={handleCancel} className="mt-4">
										Back
									</Button>
								</div>
							)}
						</div>
					)}
				</div>
			</div>
		</div>
	);
}

export const Route = createFileRoute("/2fa/setup")({
	component: TwoFactorSetupPage,
});
