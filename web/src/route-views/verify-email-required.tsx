import { IconTile } from "@/components/IconTile";
import { Layout } from "@/components/Layout";
import { Button } from "@/components/ui/button";
import { useAuthSession, useResendVerificationMutation } from "@/features/auth";
import { SecureBrandPanel } from "@/features/auth/components/AuthBrandPanel";
import { AuthSplitLayout } from "@/features/auth/components/AuthSplitLayout";
import { Link, useNavigate } from "@tanstack/react-router";
import { MailWarning } from "lucide-react";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";

export default function VerifyEmailRequiredRoute() {
	const { t } = useTranslation();
	const session = useAuthSession();
	const resendVerification = useResendVerificationMutation();
	const navigate = useNavigate();

	useEffect(() => {
		if (!session.isReady || !session.isAuthenticated) {
			return;
		}

		if (session.user?.email_verified) {
			const destination = session.user.needs_circle_onboarding
				? "/circles/onboarding"
				: "/";
			void navigate({
				to: destination === "/circles/onboarding" ? "/circles/onboarding" : "/",
				replace: true,
			});
		}
	}, [session.isAuthenticated, session.isReady, session.user?.email_verified, session.user?.needs_circle_onboarding, navigate]);

	if (!session.isReady) {
		return (
			<Layout.Loading
				showHeader={false}
				message={t("auth.verify_email_required.loading")}
			/>
		);
	}

	const email = session.user?.email ?? t("auth.verify_email_required.email_unknown");

	return (
		<AuthSplitLayout
			aside={<SecureBrandPanel />}
			icon={<IconTile icon={MailWarning} tone="amber" size="lg" />}
			eyebrow={t("auth.verify_email_required.badge")}
			title={t("auth.verify_email_required.title")}
		>
			<div className="space-y-6">
				<div className="space-y-2">
					<p
						className="text-base text-muted-foreground"
						// biome-ignore lint/security/noDangerouslySetInnerHtml: translation carries inline markup; i18next escapes the interpolated email
						dangerouslySetInnerHTML={{
							__html: t("auth.verify_email_required.message", { email }),
						}}
					/>
					<p className="text-sm text-muted-foreground">
						{t("auth.verify_email_required.instruction")}
					</p>
				</div>

				<div className="space-y-2">
					<Button
						size="lg"
						className="w-full"
						onClick={() => resendVerification.mutate()}
						isLoading={resendVerification.isPending}
						disabled={resendVerification.isPending}
					>
						{resendVerification.isPending
							? t("auth.verify_email_required.resend_sending")
							: t("auth.verify_email_required.resend_button")}
					</Button>
					<p className="text-xs text-muted-foreground">
						{t("auth.verify_email_required.spam_hint")}
					</p>
				</div>

				<div className="border-t border-border pt-6 text-sm text-muted-foreground">
					<span>{t("auth.verify_email_required.wrong_email")}</span>{" "}
					<Link
						to="/logout"
						className="font-semibold text-primary hover:text-primary/80"
					>
						{t("auth.verify_email_required.logout_link")}
					</Link>
				</div>
			</div>
		</AuthSplitLayout>
	);
}
