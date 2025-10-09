/**
 * Two-Factor Authentication Status Header
 * Displays the current 2FA status and preferred method
 */

import type { TwoFactorStatusResponse } from "../types";
import { useTranslation } from "react-i18next";

interface TwoFactorStatusHeaderProps {
	status: TwoFactorStatusResponse;
}

export function TwoFactorStatusHeader({ status }: TwoFactorStatusHeaderProps) {
	const { t } = useTranslation();
	const methodLabel = status.preferred_method
		? t(`twofa.methods.${status.preferred_method}`)
		: t("twofa.settings.no_default_method");

	return (
		<div className="bg-white rounded-lg shadow-md p-6">
			<div className="flex items-start justify-between">
				<div>
					<h1 className="text-2xl font-semibold mb-2">
						{t("twofa.title")}
					</h1>
					<div className="flex items-center gap-2">
						{status.is_enabled ? (
							<>
								<span className="inline-flex items-center bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm font-semibold">
									{t("twofa.status.enabled")}
								</span>
								<span className="text-sm text-gray-600">
									{t("twofa.status.method", {
										method: methodLabel,
									})}
								</span>
							</>
						) : (
							<span className="inline-flex items-center bg-yellow-100 text-yellow-800 px-3 py-1 rounded-full text-sm font-semibold">
								{t("twofa.status.disabled")}
							</span>
						)}
					</div>
				</div>
			</div>
		</div>
	);
}
