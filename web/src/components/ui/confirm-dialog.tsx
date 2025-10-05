/**
 * @fileoverview Confirmation dialog component.
 * Provides a pre-built dialog for confirmations with optional custom content.
 *
 * @module components/ui/confirm-dialog
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
 * Props for the ConfirmDialog component.
 */
export interface ConfirmDialogProps {
	/** Whether the dialog is open */
	open: boolean;
	/** Callback when dialog open state changes */
	onOpenChange: (open: boolean) => void;
	/** Dialog title */
	title: string;
	/** Optional description text */
	description?: string;
	/** Optional custom content to display between description and buttons */
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
 * Confirmation dialog component.
 *
 * Provides a modal dialog with title, description, optional custom content,
 * and confirm/cancel buttons. Handles loading states and prevents closing while loading.
 *
 * @example Simple confirmation
 * ```tsx
 * const [isOpen, setIsOpen] = useState(false);
 *
 * <ConfirmDialog
 *   open={isOpen}
 *   onOpenChange={setIsOpen}
 *   title="Delete Item?"
 *   description="This action cannot be undone."
 *   confirmLabel="Delete"
 *   variant="destructive"
 *   onConfirm={async () => {
 *     await deleteItem();
 *     setIsOpen(false);
 *   }}
 * />
 * ```
 *
 * @example With custom content (e.g., verification input)
 * ```tsx
 * <ConfirmDialog
 *   open={showDialog}
 *   onOpenChange={setShowDialog}
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
 * </ConfirmDialog>
 * ```
 *
 * @example Destructive action with loading state
 * ```tsx
 * const [isDeleting, setIsDeleting] = useState(false);
 *
 * <ConfirmDialog
 *   open={showDialog}
 *   onOpenChange={setShowDialog}
 *   title="Remove 2FA Method?"
 *   description="You'll need to set it up again if you want to use it."
 *   confirmLabel="Remove"
 *   variant="destructive"
 *   isLoading={isDeleting}
 *   onConfirm={async () => {
 *     setIsDeleting(true);
 *     await remove2FA();
 *     setIsDeleting(false);
 *   }}
 * />
 * ```
 */
export function ConfirmDialog({
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
}: ConfirmDialogProps) {
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
