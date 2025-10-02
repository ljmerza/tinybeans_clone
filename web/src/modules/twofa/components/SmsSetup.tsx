import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useState } from "react";
import { useInitialize2FASetup, useVerify2FASetup } from "../hooks";
import { RecoveryCodeList } from "./RecoveryCodeList";
import { VerificationInput } from "./VerificationInput";

interface SmsSetupProps {
	defaultPhone?: string;
	onComplete?: () => void;
	onCancel?: () => void;
}

type SetupStep = "intro" | "verify" | "recovery";

export function SmsSetup({ defaultPhone = "", onComplete, onCancel }: SmsSetupProps) {
	const [step, setStep] = useState<SetupStep>("intro");
	const [phone, setPhone] = useState(defaultPhone);
	const [code, setCode] = useState("");

	const initSetup = useInitialize2FASetup();
	const verifySetup = useVerify2FASetup();

	const recoveryCodes = verifySetup.data?.recovery_codes;
	const latestMessage = initSetup.data?.message ?? "Check your phone for the verification code.";

	const handleStart = async () => {
		if (!phone.trim()) return;
		try {
			await initSetup.mutateAsync({ method: "sms", phone_number: phone.trim() });
			setStep("verify");
		} catch (error) {
			console.error("SMS setup start failed:", error);
		}
	};

	const handleResend = async () => {
		if (!phone.trim()) return;
		try {
			await initSetup.mutateAsync({ method: "sms", phone_number: phone.trim() });
		} catch (error) {
			console.error("SMS setup resend failed:", error);
		}
	};

	const handleVerify = async () => {
		if (code.length !== 6) return;
		try {
			await verifySetup.mutateAsync(code);
			setStep("recovery");
		} catch (error) {
			console.error("SMS setup verification failed:", error);
			setCode("");
		}
	};

	const handleComplete = () => {
		onComplete?.();
	};

	const isPhoneValid = phone.trim().length >= 8;

	return (
		<div className="space-y-6">
			{step === "intro" && (
				<div className="space-y-4">
					<div className="text-center">
						<h2 className="text-2xl font-semibold mb-2">Verify by SMS</h2>
						<p className="text-gray-600">
							Receive a verification code via text message. Use E.164 format (e.g. +15551234567).
						</p>
					</div>

					<div className="space-y-2">
						<label className="text-sm font-medium text-gray-700" htmlFor="sms-phone">
							Phone number
						</label>
						<Input
							id="sms-phone"
							value={phone}
							onChange={(event) => setPhone(event.target.value)}
							placeholder="+15551234567"
							disabled={initSetup.isPending}
						/>
					</div>

					<div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-left">
						<h3 className="font-semibold text-blue-900 mb-2">How it works</h3>
						<ul className="text-sm text-blue-800 space-y-1 list-disc list-inside">
							<li>We send a 6-digit code via SMS.</li>
							<li>Enter the code to enable SMS-based 2FA.</li>
							<li>The SMS method becomes your default 2FA option.</li>
						</ul>
					</div>

					<div className="flex gap-2">
						<Button
							onClick={handleStart}
							disabled={!isPhoneValid || initSetup.isPending}
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
							{(initSetup.error as any)?.message || "Failed to send code. Check the phone number and try again."}
						</p>
					)}
				</div>
			)}

			{step === "verify" && (
				<div className="space-y-4">
					<div className="text-center">
						<h2 className="text-2xl font-semibold mb-2">Enter SMS Code</h2>
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
						{verifySetup.isPending ? "Verifying..." : "Verify & Enable SMS"}
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
						<h2 className="text-2xl font-semibold mb-2">✅ SMS 2FA Enabled</h2>
						<p className="text-gray-600">
							Save your recovery codes in a safe place in case you can’t receive texts.
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

