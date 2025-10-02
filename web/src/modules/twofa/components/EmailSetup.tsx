import { Button } from "@/components/ui/button";
import { useState } from "react";
import { useInitialize2FASetup, useVerify2FASetup } from "../hooks";
import { RecoveryCodeList } from "./RecoveryCodeList";
import { VerificationInput } from "./VerificationInput";

interface EmailSetupProps {
	onComplete?: () => void;
	onCancel?: () => void;
}

type SetupStep = "intro" | "verify" | "recovery";

export function EmailSetup({ onComplete, onCancel }: EmailSetupProps) {
	const [step, setStep] = useState<SetupStep>("intro");
	const [code, setCode] = useState("");

	const initSetup = useInitialize2FASetup();
	const verifySetup = useVerify2FASetup();

	const recoveryCodes = verifySetup.data?.recovery_codes;
	const latestMessage = initSetup.data?.message ?? "Check your inbox for the verification code.";

	const handleStart = async () => {
		try {
			await initSetup.mutateAsync({ method: "email" });
			setStep("verify");
		} catch (error) {
			console.error("Email setup start failed:", error);
		}
	};

	const handleResend = async () => {
		try {
			await initSetup.mutateAsync({ method: "email" });
		} catch (error) {
			console.error("Email setup resend failed:", error);
		}
	};

	const handleVerify = async () => {
		if (code.length !== 6) return;
		try {
			await verifySetup.mutateAsync(code);
			setStep("recovery");
		} catch (error) {
			console.error("Email setup verification failed:", error);
			setCode("");
		}
	};

	const handleComplete = () => {
		onComplete?.();
	};

	return (
		<div className="space-y-6">
			{step === "intro" && (
				<div className="space-y-4">
					<div className="text-center">
						<h2 className="text-2xl font-semibold mb-2">Verify by Email</h2>
						<p className="text-gray-600">
							We will send a 6-digit verification code to your account email.
						</p>
					</div>

					<div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-left">
						<h3 className="font-semibold text-blue-900 mb-2">How it works</h3>
						<ul className="text-sm text-blue-800 space-y-1 list-disc list-inside">
							<li>We send a verification code to your primary email.</li>
							<li>Enter the code to enable email-based 2FA.</li>
							<li>The email method becomes your default 2FA option.</li>
						</ul>
					</div>

					<div className="flex gap-2">
						<Button
							onClick={handleStart}
							disabled={initSetup.isPending}
							className="flex-1"
						>
							{initSetup.isPending ? "Sending..." : "Send Verification Code"}
						</Button>
						{onCancel && (
							<Button variant="outline" onClick={onCancel} className="flex-1">
								Cancel
							</Button>
						)}
					</div>

					{initSetup.error && (
						<p className="text-sm text-red-600">
							{(initSetup.error as any)?.message || "Failed to send code. Try again."}
						</p>
					)}
				</div>
			)}

			{step === "verify" && (
				<div className="space-y-4">
					<div className="text-center">
						<h2 className="text-2xl font-semibold mb-2">Enter Email Code</h2>
						<p className="text-gray-600">{latestMessage}</p>
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
						{verifySetup.isPending ? "Verifying..." : "Verify & Enable Email"}
					</Button>

					<div className="flex flex-col gap-2 sm:flex-row sm:justify-between">
						<Button
							onClick={handleResend}
							variant="ghost"
							disabled={initSetup.isPending}
							className="sm:w-auto"
						>
							Resend Code
						</Button>
						{onCancel && (
							<Button
								variant="outline"
								onClick={onCancel}
								className="sm:w-auto"
							>
								Cancel
							</Button>
						)}
					</div>

					{verifySetup.error && (
						<p className="text-sm text-red-600 text-center">
							{(verifySetup.error as any)?.message || "Invalid code. Try again."}
						</p>
					)}
				</div>
			)}

			{step === "recovery" && recoveryCodes && (
				<div className="space-y-4">
					<div className="text-center">
						<h2 className="text-2xl font-semibold mb-2">✅ Email 2FA Enabled</h2>
						<p className="text-gray-600">
							Save your recovery codes to keep access if you can’t reach your email.
						</p>
					</div>

					<RecoveryCodeList codes={recoveryCodes} showDownloadButton={true} />

					<Button onClick={handleComplete} className="w-full">
						Done
					</Button>
				</div>
			)}
		</div>
	);
}

