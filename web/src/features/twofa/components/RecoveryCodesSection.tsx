/**
 * Recovery Codes Section
 * Manage and display recovery codes for 2FA
 */

import { StatusMessage } from "@/components";
import { Button } from "@/components/ui/button";
import { RecoveryCodeList } from "./RecoveryCodeList";

interface RecoveryCodesSectionProps {
	showNewCodes: boolean;
	isGenerating: boolean;
	errMessage?: string;
	codes?: string[];
	onGenerate: () => void;
	onViewCurrent: () => void;
	onHideCodes: () => void;
}

export function RecoveryCodesSection({
	showNewCodes,
	isGenerating,
	errMessage,
	codes,
	onGenerate,
	onViewCurrent,
	onHideCodes,
}: RecoveryCodesSectionProps) {
	return (
		<div className="bg-white rounded-lg shadow-md p-6">
			<h2 className="text-xl font-semibold mb-4">Recovery Codes</h2>

			{!showNewCodes ? (
				<div className="space-y-4">
					<p className="text-gray-600 text-sm">
						Recovery codes can be used to access your account if you lose access
						to your authenticator device. Each code can only be used once.
					</p>

					<div className="flex gap-2">
						<Button
							onClick={onGenerate}
							disabled={isGenerating}
							variant="outline"
						>
							{isGenerating ? "Generating..." : "Generate New Recovery Codes"}
						</Button>

						<Button onClick={onViewCurrent} variant="outline">
							View Current Codes
						</Button>
					</div>

					{errMessage && (
						<StatusMessage variant="error">{errMessage}</StatusMessage>
					)}
				</div>
			) : (
				<div className="space-y-4">
					{codes && <RecoveryCodeList codes={codes} />}
					<Button onClick={onHideCodes} variant="outline">
						Done
					</Button>
				</div>
			)}
		</div>
	);
}
