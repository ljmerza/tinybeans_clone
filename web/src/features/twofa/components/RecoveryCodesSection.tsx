/**
 * Recovery Codes Section
 * Manage and display recovery codes for 2FA
 */

import { StatusMessage } from "@/components";
import { Button } from "@/components/ui/button";
import { useTranslation } from "react-i18next";
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
	const { t } = useTranslation();

	return (
		<div className="bg-card text-card-foreground border border-border rounded-lg shadow-md p-6 transition-colors">
			<h2 className="text-xl font-semibold text-foreground mb-4">
				{t("twofa.settings.recovery_codes_title")}
			</h2>

			{!showNewCodes ? (
				<div className="space-y-4">
					<p className="text-muted-foreground text-sm">
						{t("twofa.settings.recovery_codes_description")}
					</p>

					<div className="flex gap-2 flex-col sm:flex-row">
						<Button
							onClick={onGenerate}
							disabled={isGenerating}
							variant="outline"
							className="flex-1"
						>
							{isGenerating
								? t("twofa.settings.recovery_codes_generating")
								: t("twofa.settings.recovery_codes_generate")}
						</Button>

						<Button
							onClick={onViewCurrent}
							variant="outline"
							className="flex-1"
						>
							{t("twofa.settings.recovery_codes_view")}
						</Button>
					</div>

					{errMessage && (
						<StatusMessage variant="error">{errMessage}</StatusMessage>
					)}
				</div>
			) : (
				<div className="space-y-4">
					{codes && <RecoveryCodeList codes={codes} />}
					<Button onClick={onHideCodes} variant="outline" className="w-full">
						{t("common.done")}
					</Button>
				</div>
			)}
		</div>
	);
}
