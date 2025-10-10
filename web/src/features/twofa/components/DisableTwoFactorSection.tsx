/**
 * Disable Two-Factor Authentication Section
 * Handle the process of disabling 2FA with verification
 */

import { StatusMessage } from "@/components";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { useTranslation } from "react-i18next";
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
	const { t } = useTranslation();

	return (
		<div className="bg-card text-card-foreground border border-border rounded-lg shadow-md p-6 transition-colors">
			<h2 className="text-xl font-semibold mb-4 text-destructive">
				{t("twofa.settings.disable.title")}
			</h2>

			<div className="space-y-4">
				<p className="text-muted-foreground text-sm">
					{t("twofa.settings.disable.description")}
				</p>
				<Button onClick={onRequestDisable} variant="destructive">
					{t("twofa.settings.disable.action")}
				</Button>
			</div>

			<ConfirmDialog
				open={showDisableConfirm}
				onOpenChange={(open) => !open && onCancelDisable()}
				title={t("twofa.settings.disable.dialog_title")}
				description={t("twofa.settings.disable.dialog_description")}
				confirmLabel={
					isDisabling
						? t("twofa.settings.disable.confirm_loading")
						: t("twofa.settings.disable.confirm_label")
				}
				cancelLabel={t("common.cancel")}
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
