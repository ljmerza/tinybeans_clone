/**
 * @fileoverview Confirmation dialog with custom content area.
 * Provides a pre-built dialog for confirmations that need additional UI elements.
 *
 * @module components/ui/confirm-dialog-with-content
 */

import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import type * as React from "react";

/**
 * Props for the ConfirmDialogWithContent component.
 */
export interface ConfirmDialogWithContentProps {
	/** Whether the dialog is open */
	open: boolean;
	/** Callback when dialog open state changes */
	onOpenChange: (open: boolean) => void;
	/** Dialog title */
	title: string;
	/** Optional description text */
	description?: string;
	/** Custom content to display between description and buttons */
	children?: React.ReactNode;
	/** Label for confirm button (default: "Confirm") */
	confirmLabel?: string;
	/** Label for cancel button (default: "Cancel") */
	cancelLabel?: string;
	/** Callback when user confirms */
	onConfirm: () => void | Promise<void>;
	/** Optional callback when user cancels */
	onCancel?: () => void;
	/** Visual variant - "default" or "destructive" for dangerous actions */
	variant?: "default" | "destructive";
	/** Whether the confirm action is loading */
	isLoading?: boolean;
	/** Whether the confirm button is disabled */
	disabled?: boolean;
}

/**
 * Confirmation dialog with custom content area.
 *
 * Similar to ConfirmDialog but allows custom content between the description
 * and action buttons. Useful for confirmations that require additional input
 * (e.g., verification codes, checkboxes, or form fields).
 *
 * @example Basic usage with form input
 * ```tsx
 * <ConfirmDialogWithContent
 *   open={isOpen}
 *   onOpenChange={setIsOpen}
 *   title="Disable 2FA"
 *   description="Enter your verification code to confirm."
 *   confirmLabel="Disable"
 *   variant="destructive"
 *   disabled={!code}
 *   onConfirm={handleDisable}
 * >
 *   <VerificationInput
 *     value={code}
 *     onChange={setCode}
 *   />
 * </ConfirmDialogWithContent>
 * ```
 *
 * @example With error message
 * ```tsx
 * <ConfirmDialogWithContent
 *   open={showDialog}
 *   onOpenChange={setShowDialog}
 *   title="Confirm Action"
 *   description="This requires verification."
 *   isLoading={isProcessing}
 *   onConfirm={handleConfirm}
 * >
 *   <Input
 *     type="text"
 *     value={input}
 *     onChange={(e) => setInput(e.target.value)}
 *   />
 *   {error && (
 *     <StatusMessage variant="error">
 *       {error}
 *     </StatusMessage>
 *   )}
 * </ConfirmDialogWithContent>
 * ```
 */
export function ConfirmDialogWithContent({
	open,
	onOpenChange,
	title,
	description,
	children,
	confirmLabel = "Confirm",
	cancelLabel = "Cancel",
	onConfirm,
	onCancel,
	variant = "default",
	isLoading = false,
	disabled = false,
}: ConfirmDialogWithContentProps) {
	const handleConfirm = async () => {
		await onConfirm();
	};

	const handleCancel = () => {
		if (onCancel) {
			onCancel();
		}
		onOpenChange(false);
	};

	const handleOpenChange = (newOpen: boolean) => {
		if (!newOpen && !isLoading) {
			handleCancel();
		}
	};

	return (
		<Dialog open={open} onOpenChange={handleOpenChange}>
			<DialogContent
				className={cn(
					variant === "destructive" && "border-destructive/50 bg-destructive/5",
				)}
			>
				<DialogHeader>
					<DialogTitle
						className={cn(variant === "destructive" && "text-destructive")}
					>
						{title}
					</DialogTitle>
					{description && <DialogDescription>{description}</DialogDescription>}
				</DialogHeader>
				{children && <div className="py-4">{children}</div>}
				<DialogFooter>
					<Button variant="outline" onClick={handleCancel} disabled={isLoading}>
						{cancelLabel}
					</Button>
					<Button
						variant={variant === "destructive" ? "destructive" : "default"}
						onClick={handleConfirm}
						disabled={disabled || isLoading}
					>
						{isLoading ? "Processing..." : confirmLabel}
					</Button>
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}
