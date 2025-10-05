/**
 * @fileoverview Generic 2FA Method Card component.
 * Consolidates EmailMethodCard, SmsMethodCard, and TotpMethodCard.
 *
 * @module features/twofa/components/methods
 */

import {
	ButtonGroup,
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
	Chip,
	ChipGroup,
	StatusMessage,
} from "@/components";
import { Button } from "@/components/ui/button";
import type { ReactNode } from "react";
import type { TwoFactorMethod } from "@/features/twofa/types";

/**
 * Configuration for a chip badge
 */
export interface ChipConfig {
	/** Label text */
	label: string;
	/** Chip variant */
	variant?:
		| "neutral"
		| "primary"
		| "success"
		| "info"
		| "warning"
		| "danger"
		| "custom";
	/** Custom className */
	className?: string;
}

/**
 * Configuration for a 2FA method card
 */
export interface MethodCardConfig {
	/** Icon emoji */
	icon: string;
	/** Card title */
	title: string;
	/** Card description */
	description: string;
	/** Feature chips */
	chips: ChipConfig[];
	/** Method identifier for removal tracking */
	methodId: TwoFactorMethod;
}

interface GenericMethodCardProps {
	/** Configuration for the method */
	config: MethodCardConfig;
	/** Whether this is the current default method */
	isCurrent: boolean;
	/** Whether the method is configured */
	configured: boolean;
	/** Additional status info (e.g., phone number for SMS) */
	additionalInfo?: ReactNode;
	/** Whether removal is in progress */
	removalInProgress: boolean;
	/** The method currently being removed */
	methodToRemove: TwoFactorMethod | null;
	/** Callback to setup this method */
	onSetup: () => void;
	/** Callback to remove this method */
	onRequestRemoval: () => void;
	/** Optional callback to set as default */
	onSetAsDefault?: () => void;
	/** Whether set as default is in progress */
	setAsDefaultInProgress?: boolean;
	/** Whether to show removal button (default: true) */
	showRemoval?: boolean;
}

/**
 * Generic 2FA Method Card component.
 *
 * Displays information about a 2FA method with configuration, setup, and management options.
 * Handles three states:
 * - Not configured: Shows setup button
 * - Configured (current): Shows "Current default method" badge
 * - Configured (not current): Shows "Set as Default" and "Remove" buttons
 *
 * @example Email method card
 * ```tsx
 * <GenericMethodCard
 *   config={{
 *     icon: "📧",
 *     title: "Email Verification",
 *     description: "Receive verification codes via email.",
 *     chips: [
 *       { label: "Simple", variant: "primary" },
 *       { label: "No Extra App Needed", variant: "info" },
 *     ],
 *     methodId: "email",
 *   }}
 *   isCurrent={isCurrentMethod}
 *   configured={isConfigured}
 *   removalInProgress={removing}
 *   methodToRemove={methodBeingRemoved}
 *   onSetup={handleSetup}
 *   onRequestRemoval={handleRemove}
 *   onSetAsDefault={handleSetDefault}
 * />
 * ```
 *
 * @example SMS method with additional info
 * ```tsx
 * <GenericMethodCard
 *   config={{
 *     icon: "💬",
 *     title: "SMS Verification",
 *     description: "Receive verification codes via text message.",
 *     chips: [
 *       { label: "Quick", variant: "primary" },
 *       { label: "Requires Phone Number", className: "bg-orange-100 text-orange-800" },
 *     ],
 *     methodId: "sms",
 *   }}
 *   additionalInfo={
 *     phoneNumber && (
 *       <StatusMessage variant="info" className="text-xs">
 *         Currently sending to {phoneNumber}
 *       </StatusMessage>
 *     )
 *   }
 *   {...otherProps}
 * />
 * ```
 */
export function GenericMethodCard({
	config,
	isCurrent,
	configured,
	additionalInfo,
	removalInProgress,
	methodToRemove,
	onSetup,
	onRequestRemoval,
	onSetAsDefault,
	setAsDefaultInProgress = false,
	showRemoval = true,
}: GenericMethodCardProps) {
	return (
		<Card className="border-2 border-gray-200">
			<CardHeader className="flex items-start gap-4 pb-0">
				<div className="text-3xl">{config.icon}</div>
				<div className="flex-1 space-y-2">
					<CardTitle>{config.title}</CardTitle>
					<CardDescription>{config.description}</CardDescription>
					<ChipGroup className="mb-1">
						{config.chips.map((chip) => (
							<Chip
								key={`${chip.label}-${chip.variant}`}
								variant={chip.variant}
								className={chip.className}
							>
								{chip.label}
							</Chip>
						))}
					</ChipGroup>
					{isCurrent && (
						<StatusMessage variant="success" className="text-xs">
							Current default method
						</StatusMessage>
					)}
					{additionalInfo}
				</div>
			</CardHeader>
			<CardContent className="pt-4">
				<ButtonGroup>
					{configured ? (
						<>
							{!isCurrent && onSetAsDefault && (
								<Button
									onClick={onSetAsDefault}
									disabled={setAsDefaultInProgress}
									className="bg-green-600 hover:bg-green-700 text-white"
								>
									{setAsDefaultInProgress ? "Setting..." : "Set as Default"}
								</Button>
							)}
							{showRemoval && (
								<Button
									variant="outline"
									onClick={onRequestRemoval}
									disabled={removalInProgress}
									className="border-red-200 text-red-600 hover:bg-red-50"
								>
									{removalInProgress && methodToRemove === config.methodId
										? "Removing..."
										: "Remove"}
								</Button>
							)}
							{!showRemoval && !isCurrent && (
								<StatusMessage variant="success" className="text-sm">
									✓ Configured
								</StatusMessage>
							)}
						</>
					) : (
						<Button
							onClick={onSetup}
							className="bg-blue-600 hover:bg-blue-700 text-white"
						>
							Setup
						</Button>
					)}
				</ButtonGroup>
			</CardContent>
		</Card>
	);
}
