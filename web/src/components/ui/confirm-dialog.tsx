/**
 * @fileoverview Confirmation dialog component.
 * Provides a pre-built dialog for confirmations with optional custom content.
 *
 * @module components/ui/confirm-dialog
 */

import { Button } from "@/components/ui/button";
import {
	AlertDialog,
	AlertDialogAction,
	AlertDialogCancel,
	AlertDialogContent,
	AlertDialogDescription,
	AlertDialogFooter,
	AlertDialogHeader,
	AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { cn } from "@/lib/utils";
import type * as React from "react";
import { useId } from "react";

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
	const descriptionId = useId();

	const handleOpenChange = (newOpen: boolean) => {
		if (!newOpen) {
			if (isLoading) {
				return;
			}
			onCancel?.();
			onOpenChange(false);
		} else {
			onOpenChange(true);
		}
	};

	const handleCancelClick = (
		event: React.MouseEvent<HTMLButtonElement, MouseEvent>,
	) => {
		event.preventDefault();
		if (isLoading) {
			return;
		}
		onCancel?.();
		onOpenChange(false);
	};

	const handleConfirmClick = async (
		event: React.MouseEvent<HTMLButtonElement, MouseEvent>,
	) => {
		event.preventDefault();
		if (disabled || isLoading) {
			return;
		}
		await onConfirm();
	};

	return (
		<AlertDialog open={open} onOpenChange={handleOpenChange}>
			<AlertDialogContent
				aria-describedby={description ? descriptionId : undefined}
				className={cn(
					variant === "destructive" && "border-destructive/50 bg-destructive/5",
				)}
				onEscapeKeyDown={(event) => {
					if (isLoading) {
						event.preventDefault();
					}
				}}
				onPointerDownOutside={(event) => {
					if (isLoading) {
						event.preventDefault();
					}
				}}
				onInteractOutside={(event) => {
					if (isLoading) {
						event.preventDefault();
					}
				}}
			>
				<AlertDialogHeader>
					<AlertDialogTitle
						className={cn(variant === "destructive" && "text-destructive")}
					>
						{title}
					</AlertDialogTitle>
					{description ? (
						<AlertDialogDescription id={descriptionId}>
							{description}
						</AlertDialogDescription>
					) : null}
				</AlertDialogHeader>
				{children && <div className="py-4">{children}</div>}
				<AlertDialogFooter>
					<AlertDialogCancel asChild>
						<Button
							type="button"
							variant="outline"
							onClick={handleCancelClick}
							disabled={isLoading}
						>
							{cancelLabel}
						</Button>
					</AlertDialogCancel>
					<AlertDialogAction asChild>
						<Button
							type="button"
							variant={variant === "destructive" ? "destructive" : "default"}
							onClick={handleConfirmClick}
							disabled={disabled || isLoading}
						>
							{isLoading ? "Processing..." : confirmLabel}
						</Button>
					</AlertDialogAction>
				</AlertDialogFooter>
			</AlertDialogContent>
		</AlertDialog>
	);
}
