/**
 * @fileoverview Generic Intro Step component for 2FA setup.
 * Replaces EmailIntroStep, SmsIntroStep, and TotpIntroStep.
 *
 * @module features/twofa/components/setup/generic
 */

import {
	InfoPanel,
	StatusMessage,
	WizardFooter,
	WizardSection,
} from "@/components";
import { Button } from "@/components/ui/button";
import { useTranslation } from "react-i18next";
import type { IntroStepConfig } from "./types";

interface GenericIntroStepProps {
	/** Configuration for the step */
	config: IntroStepConfig;
	/** Whether an action is in progress */
	isLoading: boolean;
	/** Optional error message to display */
	errorMessage?: string;
	/** Callback when action button is clicked */
	onAction: () => void;
	/** Optional callback when cancel is clicked */
	onCancel?: () => void;
}

/**
 * Generic Intro Step component for 2FA setup wizards.
 *
 * Displays introductory information with an info panel and action button.
 * Supports optional custom content (e.g., phone input for SMS).
 *
 * @example Email setup
 * ```tsx
 * <GenericIntroStep
 *   config={{
 *     title: "Verify by Email",
 *     description: "We will send a 6-digit verification code to your account email.",
 *     infoPanelTitle: "How it works",
 *     infoPanelItems: [
 *       <li key="1">We send a verification code to your primary email.</li>,
 *       <li key="2">Enter the code to enable email-based 2FA.</li>,
 *     ],
 *     actionText: "Send Verification Code",
 *     loadingText: "Sending...",
 *   }}
 *   isLoading={isSending}
 *   errorMessage={error}
 *   onAction={handleSend}
 *   onCancel={handleCancel}
 * />
 * ```
 *
 * @example SMS setup with custom phone input
 * ```tsx
 * <GenericIntroStep
 *   config={{
 *     title: "Verify by SMS",
 *     description: "Receive a verification code via text message.",
 *     customContent: <Input value={phone} onChange={setPhone} />,
 *     infoPanelTitle: "How it works",
 *     infoPanelItems: [...],
 *     actionText: "Send Verification Code",
 *     loadingText: "Sending...",
 *   }}
 *   isLoading={isSending}
 *   onAction={handleSend}
 * />
 * ```
 */
export function GenericIntroStep({
	config,
	isLoading,
	errorMessage,
	onAction,
	onCancel,
}: GenericIntroStepProps) {
	const { t } = useTranslation();
	const cancelLabel = t("common.cancel");
	return (
		<>
			<WizardSection title={config.title} description={config.description}>
				{config.customContent}
				<InfoPanel title={config.infoPanelTitle}>
					<ul className="space-y-1 list-disc list-inside">
						{config.infoPanelItems.map((item, index) => (
							<li key={index}>{item}</li>
						))}
					</ul>
				</InfoPanel>
				{errorMessage && (
					<StatusMessage variant="error">{errorMessage}</StatusMessage>
				)}
			</WizardSection>
			<WizardFooter align={onCancel ? "between" : "end"}>
				<Button onClick={onAction} disabled={isLoading} className="flex-1">
					{isLoading ? config.loadingText : config.actionText}
				</Button>
				{onCancel && (
					<Button variant="outline" onClick={onCancel} className="flex-1">
						{cancelLabel}
					</Button>
				)}
			</WizardFooter>
		</>
	);
}
