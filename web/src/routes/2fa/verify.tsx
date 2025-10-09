/**
 * 2FA Verification Page
 * Used during login when 2FA is required
 */

import { StatusMessage } from "@/components";
import { AuthCard } from "@/components/AuthCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { extractApiError } from "@/features/auth/utils";
import {
	VerificationInput,
	useVerify2FALogin,
} from "@/features/twofa";
import type {
	TwoFactorMethod,
	TwoFactorVerifyState,
} from "@/features/twofa";
import { verificationCodeSchema } from "@/lib/validations/schemas/twofa";
import {
	Navigate,
	createFileRoute,
	useLocation,
	useNavigate,
} from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { z } from "zod";

const recoveryCodeSchema = z.string().min(14);

const methodLabelKey: Record<TwoFactorMethod, string> = {
	totp: "twofa.verify.methods.authenticator",
	email: "twofa.verify.methods.email",
	sms: "twofa.verify.methods.sms",
};

function TwoFactorVerifyPage() {
	const navigate = useNavigate();
	const location = useLocation();
	const { t } = useTranslation();

	const [verifyData] = useState<TwoFactorVerifyState | null>(() => {
		const state = location.state;
		if (!state || typeof state !== "object") {
			return null;
		}

		const candidate = state as Partial<TwoFactorVerifyState>;
		const partialToken = candidate.partialToken;
		const method = candidate.method;
		if (
			typeof partialToken !== "string" ||
			!method ||
			!(method in methodLabelKey)
		) {
			return null;
		}
		return {
			partialToken,
			method,
			message:
				typeof candidate.message === "string" ? candidate.message : undefined,
		} satisfies TwoFactorVerifyState;
	});

	const [code, setCode] = useState("");
	const [rememberMe, setRememberMe] = useState(false);
	const [useRecoveryCode, setUseRecoveryCode] = useState(false);

	const verify = useVerify2FALogin();

	useEffect(() => {
		if (verify.isSuccess) {
			navigate({ to: "/", replace: true });
		}
	}, [verify.isSuccess, navigate]);

	if (!verifyData?.partialToken || !verifyData?.method) {
		return <Navigate to="/login" />;
	}

	const { partialToken, method, message } = verifyData;

	const headerDescription = useMemo(() => {
		if (useRecoveryCode) {
			return t("twofa.verify.use_recovery");
		}
		if (message) {
			return message;
		}

		return t("twofa.verify.enter_code", {
			method: t(methodLabelKey[method]),
		});
	}, [method, message, t, useRecoveryCode]);

	const handleVerify = () => {
		const schema = useRecoveryCode ? recoveryCodeSchema : verificationCodeSchema;
		if (!schema.safeParse(code).success) {
			return;
		}

		verify.mutate({
			partial_token: partialToken,
			code,
			remember_me: rememberMe,
		});
	};

return (
		<AuthCard
			title={t("twofa.verify_title")}
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
					{t("common.back_to_login")}
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
					<Label htmlFor="recovery-code">
						{t("twofa.verify.recovery_label")}
					</Label>
					<Input
						id="recovery-code"
						type="text"
						placeholder={t("twofa.verify.recovery_placeholder")}
						value={code}
						onChange={(e) => setCode(e.target.value)}
						disabled={verify.isPending}
						className="text-center font-mono text-lg"
						maxLength={14}
					/>
					<p className="text-xs text-gray-500 text-center">
						{t("twofa.verify.recovery_hint")}
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
					{t("twofa.verify.remember_device")}
				</Label>
			</div>

			<Button
				onClick={handleVerify}
				disabled={
					verify.isPending ||
					!(useRecoveryCode
						? recoveryCodeSchema.safeParse(code).success
						: verificationCodeSchema.safeParse(code).success)
				}
				className="w-full"
			>
				{verify.isPending ? t("twofa.verify.verifying") : t("twofa.verify.verify")}
			</Button>

			{verify.error && (
				<div className="bg-red-50 border border-red-200 rounded p-3">
					<StatusMessage variant="error" align="center">
						{extractApiError(verify.error, t("twofa.errors.invalid_code"))}
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
						? t("twofa.verify.use_code")
						: t("twofa.verify.use_recovery_toggle")}
				</button>
			</div>
		</AuthCard>
	);
}

export const Route = createFileRoute("/2fa/verify")({
	component: TwoFactorVerifyPage,
});
