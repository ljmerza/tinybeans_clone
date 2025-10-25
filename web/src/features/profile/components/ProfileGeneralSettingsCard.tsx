import { Layout } from "@/components/Layout";
import { useAuthSession } from "@/features/auth";
import { ThemePreferenceSelect, useTheme } from "@/features/theme";
import { Link } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

export function ProfileGeneralSettingsCard() {
	const { t } = useTranslation();
	const { preference, resolvedTheme } = useTheme();
	const session = useAuthSession();
	const user = session.user;

	const selectedPreferenceLabel = t(
		`twofa.settings.general.theme.options.${preference}.title`,
	);
	const resolvedLabel = t(
		`twofa.settings.general.theme.options.${resolvedTheme}.title`,
	);

	if (session.isFetchingUser && !user) {
		return <Layout.Loading showHeader={false} layout="section" className="py-10" spinnerSize="md" message={t("common.loading", { defaultValue: "Loading..." })} />;
	}

	const emailVerified = user?.email_verified ?? false;
	const emailAddress = user?.email ?? "";

	return (
		<div className="space-y-6">
			<div className="bg-card text-card-foreground border border-border rounded-lg shadow-md p-6 space-y-4">
				<div className="space-y-2">
					<h2 className="text-xl font-semibold">
						{t("profile.general.email.title")}
					</h2>
					<p className="text-sm text-muted-foreground">
						{t("profile.general.email.description", { email: emailAddress })}
					</p>
				</div>

				<div className="space-y-3 rounded-lg border border-border/80 bg-muted/30 p-4">
					<p className="text-sm font-medium">
						{emailVerified
							? t("profile.general.email.verified_label")
							: t("profile.general.email.unverified_label")}
					</p>
					<p className="text-sm text-muted-foreground">
						{emailVerified
							? t("profile.general.email.verified_message")
							: t("profile.general.email.unverified_message")}
					</p>
					{!emailVerified ? (
						<p className="text-sm text-muted-foreground">
							{t("profile.general.email.unverified_cta")}{" "}
							<Link
								to="/verify-email-required"
								className="font-semibold text-primary hover:text-primary/80"
							>
								{t("profile.general.email.go_to_verification")}
							</Link>
						</p>
					) : null}
				</div>
			</div>

			<div className="bg-card text-card-foreground border border-border rounded-lg shadow-md p-6 space-y-6">
				<div className="space-y-2">
					<h2 className="text-xl font-semibold">
						{t("twofa.settings.general.title")}
					</h2>
					<p className="text-sm text-muted-foreground">
						{t("twofa.settings.general.description")}
					</p>
				</div>

				<div className="space-y-6">
					<div className="space-y-1">
						<h3 className="text-base font-medium">
							{t("twofa.settings.general.theme.title")}
						</h3>
						<p className="text-sm text-muted-foreground">
							{t("twofa.settings.general.theme.description")}
						</p>
					</div>

					<div className="space-y-4">
						<div className="space-y-1">
							<p className="text-sm font-medium">
								{t("twofa.settings.general.theme.select_label")}
							</p>
							<p className="text-sm text-muted-foreground">
								{t("twofa.settings.general.theme.select_description")}
							</p>
						</div>
						<ThemePreferenceSelect />
						<p className="text-xs text-muted-foreground">
							{preference === "system"
								? t("twofa.settings.general.theme.current_value_system", {
										value: resolvedLabel,
									})
								: t("twofa.settings.general.theme.current_value", {
										value: selectedPreferenceLabel,
									})}
						</p>
					</div>
				</div>
			</div>
		</div>
	);
}
