/**
 * Disable Two-Factor Authentication Section
 * Handle the process of disabling 2FA with verification
 */

import { StatusMessage } from "@/components";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { VerificationInput } from "./VerificationInput";

interface DisableTwoFactorSectionProps {
	showDisableConfirm: boolean;
	canDisable: boolean;
	disableCode: string;
	isDisabling: boolean;
	errMessage?: string;
	onRequestDisable: () => void;
	onCancelDisable: () => void;
	onCodeChange: (value: string) => void;
	onConfirmDisable: () => void;
}

export function DisableTwoFactorSection({
	showDisableConfirm,
	canDisable,
	disableCode,
	isDisabling,
	errMessage,
	onRequestDisable,
	onCancelDisable,
	onCodeChange,
	onConfirmDisable,
}: DisableTwoFactorSectionProps) {
	return (
		<div className="bg-white rounded-lg shadow-md p-6">
			<h2 className="text-xl font-semibold mb-4 text-red-600">
				Disable Two-Factor Authentication
			</h2>

			<div className="space-y-4">
				<p className="text-gray-600 text-sm">
					Disabling 2FA will make your account less secure. You'll only need
					your password to log in.
				</p>
				<Button
					onClick={onRequestDisable}
					variant="outline"
					className="text-red-600 border-red-300 hover:bg-red-50"
				>
					Disable 2FA
				</Button>
			</div>

			<ConfirmDialog
				open={showDisableConfirm}
				onOpenChange={(open) => !open && onCancelDisable()}
				title="Disable Two-Factor Authentication"
				description="Enter your 6-digit verification code to confirm disabling 2FA. This will make your account less secure."
				confirmLabel={isDisabling ? "Disabling..." : "Confirm Disable"}
				cancelLabel="Cancel"
				variant="destructive"
				isLoading={isDisabling}
				disabled={!canDisable}
				onConfirm={onConfirmDisable}
				onCancel={onCancelDisable}
			>
				<div className="space-y-4">
					<VerificationInput
						value={disableCode}
						onChange={onCodeChange}
						onComplete={onConfirmDisable}
						disabled={isDisabling}
					/>

					{errMessage && (
						<StatusMessage variant="error" align="center">
							{errMessage}
						</StatusMessage>
					)}
				</div>
			</ConfirmDialog>
		</div>
	);
}
