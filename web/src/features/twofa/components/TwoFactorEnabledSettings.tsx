/**
 * TwoFactorEnabledSettings Component
 * Shows recovery codes, trusted devices, and disable 2FA sections
 * Only visible when 2FA is enabled
 */

import { verificationCodeSchema } from "@/lib/validations";
import { DisableTwoFactorSection } from "./DisableTwoFactorSection";
import { RecoveryCodesSection } from "./RecoveryCodesSection";
import { TrustedDevicesSection } from "./TrustedDevicesSection";
import {
	useDisable2FA,
	useGenerateRecoveryCodes,
	useRequestDisableCode,
} from "../hooks";
import { useNavigate } from "@tanstack/react-router";
import { useState } from "react";

export function TwoFactorEnabledSettings() {
	const navigate = useNavigate();
	const disable2FA = useDisable2FA();
	const requestDisableCode = useRequestDisableCode();
	const generateCodes = useGenerateRecoveryCodes();

	const [showDisableConfirm, setShowDisableConfirm] = useState(false);
	const [disableCode, setDisableCode] = useState("");
	const [showNewCodes, setShowNewCodes] = useState(false);

	const handleRequestDisable = async () => {
		try {
			await requestDisableCode.mutateAsync();
			setShowDisableConfirm(true);
		} catch (error) {
			console.error("Failed to request disable code:", error);
		}
	};

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

	const canDisable = verificationCodeSchema.safeParse(disableCode).success;

	return (
		<>
			<RecoveryCodesSection
				showNewCodes={showNewCodes}
				isGenerating={generateCodes.isPending}
				errMessage={generateCodes.error?.message}
				codes={generateCodes.data?.recovery_codes}
				onGenerate={handleGenerateNewCodes}
				onViewCurrent={() => navigate({ to: "/2fa/settings" })}
				onHideCodes={() => setShowNewCodes(false)}
			/>

			<TrustedDevicesSection
				onManage={() => navigate({ to: "/2fa/trusted-devices" })}
			/>

			<DisableTwoFactorSection
				showDisableConfirm={showDisableConfirm}
				canDisable={canDisable}
				disableCode={disableCode}
				isDisabling={disable2FA.isPending}
				errMessage={
					disable2FA.error?.message || requestDisableCode.error?.message
				}
				onRequestDisable={handleRequestDisable}
				onCancelDisable={() => {
					setShowDisableConfirm(false);
					setDisableCode("");
				}}
				onCodeChange={setDisableCode}
				onConfirmDisable={handleDisable}
			/>
		</>
	);
}
