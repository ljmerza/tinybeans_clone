/**
 * Disable Two-Factor Authentication Section
 * Handle the process of disabling 2FA with verification
 */

import { StatusMessage } from "@/components";
import { Button } from "@/components/ui/button";
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

			{!showDisableConfirm ? (
				<div className="space-y-4">
					<p className="text-gray-600 text-sm">
						Disabling 2FA will make your account less secure. You'll only need your password to log in.
					</p>
					<Button
						onClick={onRequestDisable}
						variant="outline"
						className="text-red-600 border-red-300 hover:bg-red-50"
					>
						Disable 2FA
					</Button>
				</div>
			) : (
				<div className="space-y-4">
					<div className="bg-red-50 border border-red-200 rounded p-4">
						<p className="text-sm text-red-800 font-semibold mb-2">⚠️ Are you sure?</p>
						<p className="text-sm text-red-800">
							Enter your 6-digit verification code to confirm disabling 2FA.
						</p>
					</div>

					<VerificationInput
						value={disableCode}
						onChange={onCodeChange}
						onComplete={onConfirmDisable}
						disabled={isDisabling}
					/>

					<div className="flex gap-2">
						<Button
							onClick={onConfirmDisable}
							disabled={!canDisable || isDisabling}
							variant="outline"
							className="flex-1 text-red-600 border-red-300 hover:bg-red-50"
						>
							{isDisabling ? "Disabling..." : "Confirm Disable"}
						</Button>
						<Button
							onClick={onCancelDisable}
							variant="outline"
							className="flex-1"
							disabled={isDisabling}
						>
							Cancel
						</Button>
					</div>

					{errMessage && (
						<StatusMessage variant="error" align="center">{errMessage}</StatusMessage>
					)}
				</div>
			)}
		</div>
	);
}
