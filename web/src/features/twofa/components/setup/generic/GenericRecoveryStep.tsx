/**
 * @fileoverview Generic Recovery Step component for 2FA setup.
 * Replaces EmailRecoveryStep, SmsRecoveryStep, and TotpRecoveryStep.
 * 
 * @module features/twofa/components/setup/generic
 */

import { WizardFooter, WizardSection } from "@/components";
import { Button } from "@/components/ui/button";
import { RecoveryCodeList } from "../../RecoveryCodeList";
import type { RecoveryStepConfig } from "./types";

interface GenericRecoveryStepProps {
	/** Configuration for the step */
	config: RecoveryStepConfig;
	/** Recovery codes to display */
	recoveryCodes?: string[];
	/** Callback when done button is clicked */
	onComplete: () => void;
}

/**
 * Generic Recovery Step component for 2FA setup wizards.
 *
 * Final step that displays recovery codes and optional additional content.
 * Used after successful 2FA verification to show backup codes.
 *
 * @example Email recovery step
 * ```tsx
 * <GenericRecoveryStep
 *   config={{
 *     title: "✅ Email 2FA Enabled",
 *     description: "Save your recovery codes to keep access if you can't reach your email.",
 *   }}
 *   recoveryCodes={codes}
 *   onComplete={handleComplete}
 * />
 * ```
 *
 * @example TOTP recovery with success message
 * ```tsx
 * <GenericRecoveryStep
 *   config={{
 *     title: "✅ 2FA Enabled!",
 *     description: "Save your recovery codes to regain access if you lose your device.",
 *     additionalContent: (
 *       <InfoPanel variant="success" className="text-center">
 *         <p className="font-semibold">✓ Two-factor authentication is now active</p>
 *       </InfoPanel>
 *     ),
 *   }}
 *   recoveryCodes={codes}
 *   onComplete={handleComplete}
 * />
 * ```
 */
export function GenericRecoveryStep({
	config,
	recoveryCodes,
	onComplete,
}: GenericRecoveryStepProps) {
	return (
		<>
			<WizardSection title={config.title} description={config.description}>
				{recoveryCodes && (
					<RecoveryCodeList codes={recoveryCodes} showDownloadButton />
				)}
				{config.additionalContent}
			</WizardSection>
			<WizardFooter>
				<Button onClick={onComplete} className="w-full">
					Done
				</Button>
			</WizardFooter>
		</>
	);
}
