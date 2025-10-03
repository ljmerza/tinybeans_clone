/**
 * 2FA Verification Page
 * Used during login when 2FA is required
 */

import { StatusMessage } from "@/components";
import { AuthCard } from "@/components/AuthCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { verificationCodeSchema } from "@/lib/validations";
import { VerificationInput } from "@/modules/twofa/components/VerificationInput";
import { useVerify2FALogin } from "@/modules/twofa/hooks";
import type {
	TwoFactorMethod,
	TwoFactorVerifyState,
} from "@/modules/twofa/types";
import {
	Navigate,
	createFileRoute,
	useLocation,
	useNavigate,
} from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { z } from "zod";

const TWO_FACTOR_METHODS: ReadonlyArray<TwoFactorMethod> = [
	"totp",
	"email",
	"sms",
];

function isValidTwoFactorMethod(value: unknown): value is TwoFactorMethod {
	return (
		typeof value === "string" &&
		TWO_FACTOR_METHODS.includes(value as TwoFactorMethod)
	);
}

// Used in 2FA verify for recovery codes
const recoveryCodeSchema = z
	.string()
	.min(14, "Recovery code must be at least 14 characters");

function TwoFactorVerifyPage() {
	const navigate = useNavigate();
	const location = useLocation();

	// Read verify data directly from location state (no useEffect needed)
	const [verifyData] = useState<TwoFactorVerifyState | null>(() => {
		const state = location.state;
		if (!state || typeof state !== "object") {
			return null;
		}

		const candidate = state as Partial<TwoFactorVerifyState>;
		const partialToken = candidate.partialToken;
		const method = candidate.method;
		if (typeof partialToken !== "string" || !isValidTwoFactorMethod(method)) {
			return null;
		}
		const parsed: TwoFactorVerifyState = {
			partialToken,
			method,
			message:
				typeof candidate.message === "string" ? candidate.message : undefined,
		};
		console.log("2FA Verify Data from location state:", parsed);
		return parsed;
	});

	const [code, setCode] = useState("");
	const [rememberMe, setRememberMe] = useState(false);
	const [useRecoveryCode, setUseRecoveryCode] = useState(false);

	const verify = useVerify2FALogin();

	// Navigate to home on successful verification
	useEffect(() => {
		if (verify.isSuccess) {
			navigate({ to: "/", replace: true });
		}
	}, [verify.isSuccess, navigate]);

	// Redirect if no partial token (direct access or page refresh)
	if (!verifyData?.partialToken || !verifyData?.method) {
		return <Navigate to="/login" />;
	}

	const { partialToken, method, message } = verifyData;

	const handleVerify = () => {
		// Validate code based on type
		const validation = useRecoveryCode
			? recoveryCodeSchema.safeParse(code)
			: verificationCodeSchema.safeParse(code);

		if (!validation.success) return;

		console.log("Verifying 2FA code..."); // Debug log
		verify.mutate({
			partial_token: partialToken,
			code,
			remember_me: rememberMe,
		});
	};

	const getMethodDisplay = () => {
		if (useRecoveryCode) return "recovery code";
		switch (method) {
			case "totp":
				return "authenticator app";
			case "email":
				return "email";
			case "sms":
				return "phone";
			default:
				return method;
		}
	};

	const headerDescription = useRecoveryCode
		? "Enter one of your recovery codes"
		: message ?? `Enter the 6-digit code from your ${getMethodDisplay()}`;

	return (
		<AuthCard
			title="Two-Factor Authentication"
			description={headerDescription}
			className="max-w-md"
			footerClassName="border-t pt-4 text-center space-y-0"
			footer={
				<button
					type="button"
					onClick={() => navigate({ to: "/login" })}
					disabled={verify.isPending}
					className="text-sm text-gray-600 hover:text-gray-800 disabled:opacity-50"
				>
					← Back to login
				</button>
			}
		>
			{!useRecoveryCode ? (
				<VerificationInput
					value={code}
					onChange={setCode}
					onComplete={handleVerify}
					disabled={verify.isPending}
				/>
			) : (
				<div className="space-y-2">
					<Label htmlFor="recovery-code">Recovery Code</Label>
					<Input
						id="recovery-code"
						type="text"
						placeholder="XXXX-XXXX-XXXX"
						value={code}
						onChange={(e) => setCode(e.target.value)}
						disabled={verify.isPending}
						className="text-center font-mono text-lg"
						maxLength={14}
					/>
					<p className="text-xs text-gray-500 text-center">
						Format: XXXX-XXXX-XXXX (with dashes)
					</p>
				</div>
			)}

			<div className="flex items-center space-x-2">
				<input
					type="checkbox"
					id="remember-me"
					checked={rememberMe}
					onChange={(e) => setRememberMe(e.target.checked)}
					disabled={verify.isPending}
					className="h-4 w-4 rounded border-gray-300"
				/>
				<Label
					htmlFor="remember-me"
					className="text-sm font-normal cursor-pointer"
				>
					Remember this device for 30 days
				</Label>
			</div>

			<Button
				onClick={handleVerify}
				disabled={
					(useRecoveryCode
						? !recoveryCodeSchema.safeParse(code).success
						: !verificationCodeSchema.safeParse(code).success) || verify.isPending
				}
				className="w-full"
			>
				{verify.isPending ? "Verifying..." : "Verify"}
			</Button>

			{verify.error && (
				<div className="bg-red-50 border border-red-200 rounded p-3">
					<StatusMessage variant="error" align="center">
						{verify.error instanceof Error
							? verify.error.message
							: "Invalid code. Please try again."}
					</StatusMessage>
				</div>
			)}

			<div className="text-center">
				<button
					type="button"
					onClick={() => {
						setUseRecoveryCode(!useRecoveryCode);
						setCode("");
					}}
					disabled={verify.isPending}
					className="text-sm text-blue-600 hover:text-blue-800 disabled:opacity-50"
				>
					{useRecoveryCode
						? "← Use verification code instead"
						: "Use recovery code instead →"}
				</button>
			</div>
		</AuthCard>
	);
}

export const Route = createFileRoute("/2fa/verify")({
	component: TwoFactorVerifyPage,
});
