import { useTranslation } from "react-i18next";

import {
	EmailMethodCard,
	SmsMethodCard,
	TotpMethodCard,
	TwoFactorEnabledSettings,
	TwoFactorStatusHeader,
} from ".";
import type { TwoFactorMethod, TwoFactorStatusResponse } from "../types";

const setupRoutes: Record<
	TwoFactorMethod,
	`/profile/2fa/setup/${TwoFactorMethod}`
> = {
	totp: "/profile/2fa/setup/totp",
	email: "/profile/2fa/setup/email",
	sms: "/profile/2fa/setup/sms",
};

interface TwoFactorSettingsContentProps {
	status: TwoFactorStatusResponse;
	removalError: string | null;
	switchError: string | null;
	methodToRemove: TwoFactorMethod | null;
	removalInProgress: boolean;
	switchInProgress: boolean;
	onRequestRemoval: (method: TwoFactorMethod) => void;
	onSetAsDefault: (method: TwoFactorMethod) => void;
	onNavigateToSetup: (path: string) => void;
}

export function TwoFactorSettingsContent({
	status,
	removalError,
	switchError,
	methodToRemove,
	removalInProgress,
	switchInProgress,
	onRequestRemoval,
	onSetAsDefault,
	onNavigateToSetup,
}: TwoFactorSettingsContentProps) {
	const { t } = useTranslation();

	const preferredMethod = status.preferred_method ?? null;
	const totpConfigured = Boolean(status.has_totp);
	const smsConfigured = Boolean(status.has_sms);
	const emailConfigured = Boolean(status.has_email);
	const phoneNumber = status.phone_number;
	const emailAddress = status.email_address ?? status.backup_email ?? undefined;

	return (
		<div className="space-y-6">
			<TwoFactorStatusHeader status={status} />

			<div className="bg-card text-card-foreground border border-border rounded-lg shadow-md p-6 space-y-6 transition-colors">
				<div className="flex items-start justify-between">
					<div>
						<h2 className="text-xl font-semibold text-foreground mb-1">
							{t("twofa.settings.manage_title")}
						</h2>
						<p className="text-sm text-muted-foreground">
							{t("twofa.settings.manage_description")}
						</p>
					</div>
				</div>

				{!status.is_enabled ? (
					<div className="bg-amber-500/15 border border-amber-500/30 dark:border-amber-500/40 text-sm rounded-lg p-4 transition-colors">
						<p className="font-semibold">
							{t("twofa.settings.not_enabled_title")}
						</p>
						<p className="text-muted-foreground">
							{t("twofa.settings.not_enabled_description")}
						</p>
					</div>
				) : null}

				{removalError ? (
					<p className="text-sm text-destructive bg-destructive/10 border border-destructive/30 dark:border-destructive/40 rounded px-4 py-3 transition-colors">
						{removalError}
					</p>
				) : null}

				{switchError ? (
					<p className="text-sm text-destructive bg-destructive/10 border border-destructive/30 dark:border-destructive/40 rounded px-4 py-3 transition-colors">
						{switchError}
					</p>
				) : null}

				<div className="space-y-4">
					<TotpMethodCard
						isCurrent={preferredMethod === "totp"}
						configured={totpConfigured}
						removalInProgress={removalInProgress}
						methodToRemove={methodToRemove}
						onSetup={() => onNavigateToSetup(setupRoutes.totp)}
						onRequestRemoval={() => onRequestRemoval("totp")}
						onSetAsDefault={() => onSetAsDefault("totp")}
						setAsDefaultInProgress={switchInProgress}
					/>

					<EmailMethodCard
						isCurrent={preferredMethod === "email"}
						configured={emailConfigured}
						emailAddress={emailAddress}
						onSetup={() => onNavigateToSetup(setupRoutes.email)}
						onSetAsDefault={() => onSetAsDefault("email")}
						setAsDefaultInProgress={switchInProgress}
						onRequestRemoval={() => onRequestRemoval("email")}
						removalInProgress={removalInProgress}
						methodToRemove={methodToRemove}
					/>

					<SmsMethodCard
						isCurrent={preferredMethod === "sms"}
						configured={smsConfigured}
						phoneNumber={phoneNumber}
						removalInProgress={removalInProgress}
						methodToRemove={methodToRemove}
						onSetup={() => onNavigateToSetup(setupRoutes.sms)}
						onRequestRemoval={() => onRequestRemoval("sms")}
						onSetAsDefault={() => onSetAsDefault("sms")}
						setAsDefaultInProgress={switchInProgress}
					/>
				</div>
			</div>

			{status.is_enabled ? <TwoFactorEnabledSettings /> : null}
		</div>
	);
}
