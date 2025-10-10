/**
 * @fileoverview Generic setup step components for 2FA methods.
 * Consolidates duplicate Email/SMS/TOTP setup step components into reusable generics.
 *
 * @module features/twofa/components/setup/generic
 */

import type { ReactNode } from "react";

export interface InfoPanelItem {
	/** Unique identifier for the info panel item */
	id: string;
	/** Display content for the item */
	content: ReactNode;
}

/**
 * Configuration for the Intro step
 */
export interface IntroStepConfig {
	/** Step title */
	title: string;
	/** Step description */
	description: string;
	/** Info panel title */
	infoPanelTitle: string;
	/** Info panel content items */
	infoPanelItems: InfoPanelItem[];
	/** Custom content (e.g., phone input for SMS) */
	customContent?: ReactNode;
	/** Action button text */
	actionText: string;
	/** Loading state button text */
	loadingText: string;
}

/**
 * Configuration for the Verify step
 */
export interface VerifyStepConfig {
	/** Step title */
	title: string;
	/** Verification button text */
	verifyButtonText: string;
	/** Loading state text */
	loadingText: string;
	/** Whether to show resend functionality */
	showResend?: boolean;
	/** Resend button text (if showResend is true) */
	resendButtonText?: string;
	/** Back button text (for non-resend variants) */
	backButtonText?: string;
}

/**
 * Configuration for the Recovery step
 */
export interface RecoveryStepConfig {
	/** Step title */
	title: string;
	/** Step description */
	description: string;
	/** Additional content (e.g., success message) */
	additionalContent?: ReactNode;
}
