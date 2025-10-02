/**
 * TOTP (Authenticator App) Setup Component
 */

import { Button } from "@/components/ui/button";
import { useState } from "react";
import { useInitialize2FASetup, useVerify2FASetup } from "../hooks";
import { QRCodeDisplay } from "./QRCodeDisplay";
import { RecoveryCodeList } from "./RecoveryCodeList";
import { VerificationInput } from "./VerificationInput";

interface TotpSetupProps {
	onComplete?: () => void;
	onCancel?: () => void;
}

export function TotpSetup({ onComplete, onCancel }: TotpSetupProps) {
	const [step, setStep] = useState<"initial" | "scan" | "verify" | "recovery">(
		"initial",
	);
	const [code, setCode] = useState("");

	const initSetup = useInitialize2FASetup();
	const verifySetup = useVerify2FASetup();

	const setupData = initSetup.data;
	const recoveryCodes = verifySetup.data?.recovery_codes;

	const handleInitialize = async () => {
		try {
			await initSetup.mutateAsync({ method: "totp" });
			setStep("scan");
		} catch (error) {
			console.error("Setup initialization failed:", error);
		}
	};

	const handleVerify = async () => {
		if (code.length !== 6) return;

		try {
			await verifySetup.mutateAsync(code);
			setStep("recovery");
		} catch (error) {
			console.error("Verification failed:", error);
			setCode("");
		}
	};

	const handleComplete = () => {
		if (onComplete) {
			onComplete();
		}
	};

	return (
		<div className="space-y-6">
			{/* Step 1: Initial */}
			{step === "initial" && (
				<div className="text-center space-y-4">
					<div className="mb-6">
						<h2 className="text-2xl font-semibold mb-2">
							Set up Authenticator App
						</h2>
						<p className="text-gray-600">
							Use an authenticator app to generate verification codes for
							enhanced security.
						</p>
					</div>

					<div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-left">
						<h3 className="font-semibold text-blue-900 mb-2">
							What you'll need:
						</h3>
						<ul className="text-sm text-blue-800 space-y-1 list-disc list-inside">
							<li>A smartphone or tablet</li>
							<li>
								An authenticator app (Google Authenticator, Authy, 1Password,
								etc.)
							</li>
							<li>A few minutes to complete setup</li>
						</ul>
					</div>

					<div className="flex gap-2">
						<Button
							onClick={handleInitialize}
							disabled={initSetup.isPending}
							className="flex-1"
						>
							{initSetup.isPending ? "Setting up..." : "Start Setup"}
						</Button>
						{onCancel && (
							<Button variant="outline" onClick={onCancel} className="flex-1">
								Cancel
							</Button>
						)}
					</div>

					{initSetup.error && (
						<p className="text-sm text-red-600">
							{(initSetup.error as any)?.message ||
								"Setup failed. Please try again."}
						</p>
					)}
				</div>
			)}

			{/* Step 2: Scan QR Code */}
			{step === "scan" && setupData && (
				<div className="space-y-4">
					<div className="text-center mb-4">
						<h2 className="text-2xl font-semibold mb-2">Scan QR Code</h2>
						<p className="text-gray-600">
							Open your authenticator app and scan this QR code
						</p>
					</div>

					<QRCodeDisplay
						qrCodeImage={setupData.qr_code_image!}
						secret={setupData.secret!}
					/>

					<Button onClick={() => setStep("verify")} className="w-full">
						I've Scanned the Code
					</Button>
				</div>
			)}

			{/* Step 3: Verify Code */}
			{step === "verify" && (
				<div className="space-y-4">
					<div className="text-center mb-4">
						<h2 className="text-2xl font-semibold mb-2">Verify Setup</h2>
						<p className="text-gray-600">
							Enter the 6-digit code from your authenticator app to verify
						</p>
					</div>

					<VerificationInput
						value={code}
						onChange={setCode}
						onComplete={handleVerify}
						disabled={verifySetup.isPending}
					/>

					<Button
						onClick={handleVerify}
						disabled={code.length !== 6 || verifySetup.isPending}
						className="w-full"
					>
						{verifySetup.isPending ? "Verifying..." : "Verify & Enable 2FA"}
					</Button>

					{verifySetup.error && (
						<p className="text-sm text-red-600 text-center">
							{(verifySetup.error as any)?.message ||
								"Invalid code. Please try again."}
						</p>
					)}

					<Button
						variant="ghost"
						onClick={() => setStep("scan")}
						className="w-full"
						disabled={verifySetup.isPending}
					>
						Back to QR Code
					</Button>
				</div>
			)}

			{/* Step 4: Recovery Codes */}
			{step === "recovery" && recoveryCodes && (
				<div className="space-y-4">
					<div className="text-center mb-4">
						<h2 className="text-2xl font-semibold mb-2">✅ 2FA Enabled!</h2>
						<p className="text-gray-600">
							Save your recovery codes to regain access if you lose your device
						</p>
					</div>

					<RecoveryCodeList codes={recoveryCodes} showDownloadButton={true} />

					<div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center">
						<p className="text-sm text-green-800 font-semibold">
							✓ Two-factor authentication is now active
						</p>
					</div>

					<Button onClick={handleComplete} className="w-full">
						Done
					</Button>
				</div>
			)}
		</div>
	);
}
