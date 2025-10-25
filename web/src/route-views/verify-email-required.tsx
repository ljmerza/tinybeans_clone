import { Layout } from "@/components/Layout";
import { Button } from "@/components/ui/button";
import { useAuthSession, useResendVerificationMutation } from "@/features/auth";
import { Link, useNavigate } from "@tanstack/react-router";
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
		<Layout showHeader={false}>
			<div className="mx-auto max-w-lg space-y-6 rounded-2xl border border-border bg-card/90 p-8 text-center shadow-lg">
				<p className="text-xs font-semibold uppercase tracking-wide text-primary">
					{t("auth.verify_email_required.badge")}
				</p>
				<h1 className="heading-2">
					{t("auth.verify_email_required.title")}
				</h1>
				<p
					className="text-base text-muted-foreground"
					dangerouslySetInnerHTML={{
						__html: t("auth.verify_email_required.message", { email }),
					}}
				/>
				<p className="text-sm text-muted-foreground">
					{t("auth.verify_email_required.instruction")}
				</p>

				<div className="space-y-2">
					<Button
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

				<div className="text-sm text-muted-foreground">
					<span>{t("auth.verify_email_required.wrong_email")}</span>{" "}
					<Link
						to="/logout"
						className="font-semibold text-primary hover:text-primary/80"
					>
						{t("auth.verify_email_required.logout_link")}
					</Link>
				</div>
			</div>
		</Layout>
	);
}
