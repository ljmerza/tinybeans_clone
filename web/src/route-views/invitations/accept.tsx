import { Button } from "@/components/ui/button";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { StandardError } from "@/components/StandardError";
import { useAuthSession } from "@/features/auth";
import {
	loadStoredInvitation,
	useStartCircleInvitationOnboarding,
} from "@/features/circles/hooks/useCircleInvitationOnboarding";
import type { CircleInvitationOnboardingStart } from "@/features/circles";
import type { ApiError } from "@/types";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Route } from "@/routes/invitations.accept";

function InvitationAcceptRouteView() {
	const { t } = useTranslation();
	const { token } = Route.useSearch();
	const navigate = Route.useNavigate();
	const session = useAuthSession();
	const startMutation = useStartCircleInvitationOnboarding();

	useEffect(() => {
		if (!token) return;
		startMutation.mutate(token);
	}, [startMutation, token]);

	if (!token) {
		return (
			<StandardError
				title={t("pages.inviteAccept.invalidTitle")}
				message={t("pages.inviteAccept.invalidMessage")}
			/>
		);
	}

	if (startMutation.isLoading) {
		return (
			<div className="flex min-h-[50vh] items-center justify-center">
				<LoadingSpinner label={t("pages.inviteAccept.loading") ?? ""} />
			</div>
		);
	}

	if (startMutation.isError) {
		const error = startMutation.error as ApiError;
		return (
			<StandardError
				title={t("pages.inviteAccept.invalidTitle")}
				message={error.message ?? t("pages.inviteAccept.invalidMessage")}
			/>
		);
	}

	const payload = (startMutation.data?.data ?? startMutation.data) as
		| CircleInvitationOnboardingStart
		| undefined;

	if (!payload) {
		return null;
	}

	const { invitation } = payload;
	const circleName = invitation.circle?.name ?? "";
	const existingUser = invitation.existing_user;
	const stored = loadStoredInvitation();
	const showFinalizing =
		session.status === "authenticated" && Boolean(stored?.onboardingToken);

	return (
		<div className="mx-auto flex min-h-[60vh] max-w-2xl flex-col gap-6 py-12">
			<header className="space-y-2 text-center">
				<h1 className="heading-2">
					{t("pages.inviteAccept.title", { circle: circleName })}
				</h1>
				<p className="text-muted-foreground">
					{t("pages.inviteAccept.subtitle", { circle: circleName })}
				</p>
			</header>

			<section className="rounded-lg border border-border bg-card p-6 shadow-sm">
				<h2 className="text-lg font-semibold">
					{existingUser
						? t("pages.inviteAccept.existingUserHeading")
						: t("pages.inviteAccept.newUserHeading")}
				</h2>
				<p className="text-sm text-muted-foreground">
					{existingUser
						? t("pages.inviteAccept.existingUserDescription")
						: t("pages.inviteAccept.newUserDescription")}
				</p>
				<div className="mt-4 flex flex-wrap gap-3">
					<Button onClick={() => navigate({ to: "/login" })} variant={existingUser ? "default" : "outline"}>
						{t("pages.inviteAccept.login")}
					</Button>
					<Button onClick={() => navigate({ to: "/signup" })} variant={existingUser ? "outline" : "default"}>
						{t("pages.inviteAccept.signup")}
					</Button>
				</div>
			</section>

			{showFinalizing ? (
				<section className="flex items-center gap-3 rounded-lg border border-border bg-muted/60 p-4 text-sm text-muted-foreground">
					<LoadingSpinner size="small" />
					<span>{t("pages.inviteAccept.finalizing")}</span>
				</section>
			) : null}
		</div>
	);
}

export default InvitationAcceptRouteView;
