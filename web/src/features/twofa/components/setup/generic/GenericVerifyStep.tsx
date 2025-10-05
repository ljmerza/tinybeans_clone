/**
 * @fileoverview Generic Verify Step component for 2FA setup.
 * Replaces EmailVerifyStep, SmsVerifyStep, and TotpVerifyStep.
 *
 * @module features/twofa/components/setup/generic
 */

import {
	ButtonGroup,
	StatusMessage,
	WizardFooter,
	WizardSection,
} from "@/components";
import { Button } from "@/components/ui/button";
import { verificationCodeSchema } from "@/lib/validations/schemas/twofa";
import { VerificationInput } from "../../VerificationInput";
import type { VerifyStepConfig } from "./types";

interface GenericVerifyStepProps {
	/** Configuration for the step */
	config: VerifyStepConfig;
	/** Current verification code value */
	code: string;
	/** Description/message to display */
	message: string;
	/** Whether verification is in progress */
	isVerifying: boolean;
	/** Whether resend is in progress (only used if config.showResend is true) */
	isResending?: boolean;
	/** Optional error message to display */
	errorMessage?: string;
	/** Callback when code changes */
	onCodeChange: (value: string) => void;
	/** Callback when verify button is clicked */
	onVerify: (value?: string) => void;
	/** Callback for resend action (required if config.showResend is true) */
	onResend?: () => void;
	/** Callback for back/cancel action */
	onSecondaryAction?: () => void;
}

/**
 * Generic Verify Step component for 2FA setup wizards.
 *
 * Displays a verification code input with primary action button.
 * Supports two variants:
 * - With resend functionality (Email/SMS)
 * - With back button (TOTP)
 *
 * @example Email/SMS verification with resend
 * ```tsx
 * <GenericVerifyStep
 *   config={{
 *     title: "Enter Email Code",
 *     verifyButtonText: "Verify & Enable Email",
 *     loadingText: "Verifying...",
 *     showResend: true,
 *     resendButtonText: "Resend Code",
 *   }}
 *   code={code}
 *   message="We sent a 6-digit code to your email."
 *   isVerifying={isVerifying}
 *   isResending={isResending}
 *   onCodeChange={setCode}
 *   onVerify={handleVerify}
 *   onResend={handleResend}
 *   onSecondaryAction={handleCancel}
 * />
 * ```
 *
 * @example TOTP verification with back button
 * ```tsx
 * <GenericVerifyStep
 *   config={{
 *     title: "Verify Setup",
 *     verifyButtonText: "Verify & Enable 2FA",
 *     loadingText: "Verifying...",
 *     showResend: false,
 *     backButtonText: "Back to QR Code",
 *   }}
 *   code={code}
 *   message="Enter the 6-digit code from your authenticator app."
 *   isVerifying={isVerifying}
 *   onCodeChange={setCode}
 *   onVerify={handleVerify}
 *   onSecondaryAction={handleBack}
 * />
 * ```
 */
export function GenericVerifyStep({
	config,
	code,
	message,
	isVerifying,
	isResending = false,
	errorMessage,
	onCodeChange,
	onVerify,
	onResend,
	onSecondaryAction,
}: GenericVerifyStepProps) {
	const isCodeValid = verificationCodeSchema.safeParse(code).success;

	return (
		<>
			<WizardSection title={config.title} description={message}>
				<VerificationInput
					value={code}
					onChange={onCodeChange}
					onComplete={(val) => onVerify(val)}
					disabled={isVerifying}
				/>
				{config.showResend && onResend ? (
					<ButtonGroup className="flex-col sm:flex-row sm:justify-between">
						<Button
							onClick={onResend}
							variant="ghost"
							disabled={isResending}
							className="sm:w-auto"
						>
							{config.resendButtonText || "Resend Code"}
						</Button>
						{onSecondaryAction && (
							<Button
								variant="outline"
								onClick={onSecondaryAction}
								className="sm:w-auto"
							>
								Cancel
							</Button>
						)}
					</ButtonGroup>
				) : null}
				{errorMessage && (
					<StatusMessage variant="error" align="center">
						{errorMessage}
					</StatusMessage>
				)}
			</WizardSection>
			<WizardFooter align={config.showResend ? "end" : "between"}>
				{!config.showResend && onSecondaryAction && (
					<Button
						variant="ghost"
						onClick={onSecondaryAction}
						disabled={isVerifying}
						className="flex-1 sm:flex-none"
					>
						{config.backButtonText || "Back"}
					</Button>
				)}
				<Button
					onClick={() => onVerify()}
					disabled={!isCodeValid || isVerifying}
					className={config.showResend ? "w-full" : "flex-1 sm:flex-none"}
				>
					{isVerifying ? config.loadingText : config.verifyButtonText}
				</Button>
			</WizardFooter>
		</>
	);
}
