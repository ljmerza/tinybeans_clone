import { ConfirmDialog } from "@/components";
import { useTranslation } from "react-i18next";

import type { TwoFactorMethod } from "../types";

interface TwoFactorRemovalDialogProps {
	method: TwoFactorMethod | null;
	isLoading: boolean;
	onConfirm: () => void;
	onCancel: () => void;
}

export function TwoFactorRemovalDialog({
	method,
	isLoading,
	onConfirm,
	onCancel,
}: TwoFactorRemovalDialogProps) {
	const { t } = useTranslation();

	const methodLabel = method ? t(`twofa.methods.${method}`) : "";
	const removalDescription = method
		? t(`twofa.settings.remove_description.${method}`)
		: "";

	return (
		<ConfirmDialog
			open={Boolean(method)}
			onOpenChange={(open) => {
				if (!open) {
					onCancel();
				}
			}}
			title={
				method
					? t("twofa.settings.remove_title", { method: methodLabel })
					: ""
			}
			description={removalDescription}
			confirmLabel={t("common.remove")}
			cancelLabel={t("common.cancel")}
			variant="destructive"
			isLoading={isLoading}
			onConfirm={onConfirm}
			onCancel={onCancel}
		/>
	);
}
