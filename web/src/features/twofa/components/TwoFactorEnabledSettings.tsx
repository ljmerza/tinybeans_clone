/**
 * TwoFactorEnabledSettings Component
 * Shows recovery codes, trusted devices, and disable 2FA sections
 * Only visible when 2FA is enabled
 */

import { extractApiError } from "@/features/auth/utils";
import { verificationCodeSchema } from "@/lib/validations/schemas/twofa";
import { useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
	useDisable2FA,
	useGenerateRecoveryCodes,
	useRequestDisableCode,
} from "../hooks";
import type { RecoveryCodesResponse } from "../types";
import { unwrapApiResponse } from "../utils/unwrapApiResponse";
import { DisableTwoFactorSection } from "./DisableTwoFactorSection";
import { RecoveryCodesSection } from "./RecoveryCodesSection";
import { TrustedDevicesSection } from "./TrustedDevicesSection";

export function TwoFactorEnabledSettings() {
	const navigate = useNavigate();
	const { t } = useTranslation();
	const disable2FA = useDisable2FA();
	const requestDisableCode = useRequestDisableCode();
	const generateCodes = useGenerateRecoveryCodes();
	const generatedCodesPayload = unwrapApiResponse<RecoveryCodesResponse>(
		generateCodes.data,
	);

	const [showDisableConfirm, setShowDisableConfirm] = useState(false);
	const [disableCode, setDisableCode] = useState("");
	const [showNewCodes, setShowNewCodes] = useState(false);
	const [disableErrorMessage, setDisableErrorMessage] = useState<string | null>(
		null,
	);
	const [generateErrorMessage, setGenerateErrorMessage] = useState<
		string | null
	>(null);

	const handleRequestDisable = async () => {
		setDisableErrorMessage(null);
		try {
			await requestDisableCode.mutateAsync();
			setShowDisableConfirm(true);
		} catch (error) {
			const message = extractApiError(error, t("twofa.errors.request_disable"));
			setDisableErrorMessage(message);
		}
	};

	const handleDisable = async () => {
		const validation = verificationCodeSchema.safeParse(disableCode);
		if (!validation.success) return;

		setDisableErrorMessage(null);
		try {
			await disable2FA.mutateAsync(disableCode);
			navigate({ to: "/" });
		} catch (error) {
			setDisableCode("");
			const message = extractApiError(error, t("twofa.errors.disable"));
			setDisableErrorMessage(message);
		}
	};

	const handleGenerateNewCodes = async () => {
		setGenerateErrorMessage(null);
		try {
			await generateCodes.mutateAsync();
			setShowNewCodes(true);
		} catch (error) {
			const message = extractApiError(error, t("twofa.errors.generate_codes"));
			setGenerateErrorMessage(message);
		}
	};

	const canDisable = verificationCodeSchema.safeParse(disableCode).success;

	return (
		<>
			<RecoveryCodesSection
				showNewCodes={showNewCodes}
				isGenerating={generateCodes.isPending}
				errMessage={
					generateErrorMessage ?? generateCodes.error?.message ?? undefined
				}
				codes={generatedCodesPayload?.recovery_codes}
				onGenerate={handleGenerateNewCodes}
				onHideCodes={() => {
					setShowNewCodes(false);
					setGenerateErrorMessage(null);
				}}
			/>

			<TrustedDevicesSection
				onManage={() => navigate({ to: "/profile/2fa/trusted-devices" })}
			/>

			<DisableTwoFactorSection
				showDisableConfirm={showDisableConfirm}
				canDisable={canDisable}
				disableCode={disableCode}
				isDisabling={disable2FA.isPending}
				errMessage={
					disableErrorMessage ??
					disable2FA.error?.message ??
					requestDisableCode.error?.message ??
					undefined
				}
				onRequestDisable={handleRequestDisable}
				onCancelDisable={() => {
					setShowDisableConfirm(false);
					setDisableCode("");
					setDisableErrorMessage(null);
				}}
				onCodeChange={setDisableCode}
				onConfirmDisable={handleDisable}
			/>
		</>
	);
}
