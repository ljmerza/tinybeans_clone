/**
 * TwoFactorEnabledSettings Component
 * Shows recovery codes, trusted devices, and disable 2FA sections
 * Only visible when 2FA is enabled
 */

import { DisableTwoFactorSection } from "@/modules/twofa/components/DisableTwoFactorSection";
import { RecoveryCodesSection } from "@/modules/twofa/components/RecoveryCodesSection";
import { TrustedDevicesSection } from "@/modules/twofa/components/TrustedDevicesSection";

interface TwoFactorEnabledSettingsProps {
	// Recovery codes props
	showNewCodes: boolean;
	isGenerating: boolean;
	generationError?: string;
	codes?: string[];
	onGenerate: () => void;
	onViewCurrent: () => void;
	onHideCodes: () => void;

	// Trusted devices props
	onManageTrustedDevices: () => void;

	// Disable 2FA props
	showDisableConfirm: boolean;
	canDisable: boolean;
	disableCode: string;
	isDisabling: boolean;
	disableError?: string;
	onRequestDisable: () => void;
	onCancelDisable: () => void;
	onCodeChange: (code: string) => void;
	onConfirmDisable: () => void;
}

export function TwoFactorEnabledSettings({
	showNewCodes,
	isGenerating,
	generationError,
	codes,
	onGenerate,
	onViewCurrent,
	onHideCodes,
	onManageTrustedDevices,
	showDisableConfirm,
	canDisable,
	disableCode,
	isDisabling,
	disableError,
	onRequestDisable,
	onCancelDisable,
	onCodeChange,
	onConfirmDisable,
}: TwoFactorEnabledSettingsProps) {
	return (
		<>
			<RecoveryCodesSection
				showNewCodes={showNewCodes}
				isGenerating={isGenerating}
				errMessage={generationError}
				codes={codes}
				onGenerate={onGenerate}
				onViewCurrent={onViewCurrent}
				onHideCodes={onHideCodes}
			/>

			<TrustedDevicesSection onManage={onManageTrustedDevices} />

			<DisableTwoFactorSection
				showDisableConfirm={showDisableConfirm}
				canDisable={canDisable}
				disableCode={disableCode}
				isDisabling={isDisabling}
				errMessage={disableError}
				onRequestDisable={onRequestDisable}
				onCancelDisable={onCancelDisable}
				onCodeChange={onCodeChange}
				onConfirmDisable={onConfirmDisable}
			/>
		</>
	);
}
