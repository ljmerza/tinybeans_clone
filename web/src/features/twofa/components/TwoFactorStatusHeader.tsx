/**
 * Two-Factor Authentication Status Header
 * Displays the current 2FA status and preferred method
 */

import { useTranslation } from "react-i18next";
import type { TwoFactorStatusResponse } from "../types";

interface TwoFactorStatusHeaderProps {
	status: TwoFactorStatusResponse;
}

export function TwoFactorStatusHeader({ status }: TwoFactorStatusHeaderProps) {
	const { t } = useTranslation();
	const methodLabel = status.preferred_method
		? t(`twofa.methods.${status.preferred_method}`)
		: t("twofa.settings.no_default_method");

	return (
		<div className="bg-card text-card-foreground border border-border rounded-lg shadow-md p-6 transition-colors">
			<div className="flex items-start justify-between">
				<div>
					<h1 className="text-2xl font-semibold text-foreground mb-2">
						{t("twofa.title")}
					</h1>
					<div className="flex items-center gap-2">
						{status.is_enabled ? (
							<>
								<span className="inline-flex items-center bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 px-3 py-1 rounded-full text-sm font-semibold">
									{t("twofa.status.enabled")}
								</span>
								<span className="text-sm text-muted-foreground">
									{t("twofa.status.method", {
										method: methodLabel,
									})}
								</span>
							</>
						) : (
							<span className="inline-flex items-center bg-amber-500/15 text-amber-700 dark:text-amber-300 px-3 py-1 rounded-full text-sm font-semibold">
								{t("twofa.status.disabled")}
							</span>
						)}
					</div>
				</div>
			</div>
		</div>
	);
}
