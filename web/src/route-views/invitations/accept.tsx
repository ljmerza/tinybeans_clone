import { Card, CardContent, CardHeader, CardTitle } from "@/components/Card";
import { Layout } from "@/components/Layout";
import { StatusMessage } from "@/components/StatusMessage";
import { Button } from "@/components/ui/button";
import { useInvitationAcceptance } from "@/features/circles/hooks/useInvitationAcceptance";
import { useLocation } from "@tanstack/react-router";
import { useMemo } from "react";
import { useTranslation } from "react-i18next";

import { Route } from "@/routes/invitations.accept";

interface InvitationAcceptContentProps {
	token?: string;
}

export function InvitationAcceptContent({
	token,
}: InvitationAcceptContentProps) {
	const { t } = useTranslation();
	const location = useLocation();
	const navigate = Route.useNavigate();
	const { token: inviteTokenParam } = Route.useSearch();

	const currentPath = useMemo(() => {
		if (!inviteTokenParam) {
			return location.pathname;
		}
		const query = new URLSearchParams({ token: inviteTokenParam }).toString();
		return `${location.pathname}?${query}`;
	}, [inviteTokenParam, location.pathname]);

	const {
		viewState,
		invitationDetails,
		errorMessage,
		isLoading,
		mutations,
		handleAccept,
		handleDecline,
	} = useInvitationAcceptance({
		token,
		currentPath,
		navigate,
	});

	if (viewState === "invalid") {
		return (
			<div className="flex min-h-[60vh] items-center justify-center px-4">
				<StatusMessage variant="error">
					{t("pages.inviteAccept.invalidMessage")}
				</StatusMessage>
			</div>
		);
	}

	const circleName = invitationDetails?.circle?.name ?? "";
	const invitedBy = invitationDetails?.invited_by?.username;

	return (
		<div className="mx-auto flex min-h-[60vh] max-w-2xl flex-col gap-6 py-12">
			<header className="space-y-2 text-center">
				<h1 className="heading-2">
					{circleName
						? t("pages.inviteAccept.title", { circle: circleName })
						: t("pages.inviteAccept.genericTitle")}
				</h1>
				<p className="text-muted-foreground">
					{circleName
						? t("pages.inviteAccept.subtitle", { circle: circleName })
						: t("pages.inviteAccept.genericSubtitle")}
				</p>
			</header>

			{isLoading ? (
				<Layout.Loading
					showHeader={false}
					layout="section"
					className="min-h-[30vh]"
					message={t("pages.inviteAccept.loading")}
					spinnerSize="md"
				/>
			) : null}

			{viewState === "expired" ? (
				<StatusMessage variant="warning">
					{t("pages.inviteAccept.expired")}
				</StatusMessage>
			) : null}

			{viewState === "error" && errorMessage ? (
				<StatusMessage variant="error">{errorMessage}</StatusMessage>
			) : null}

			{["pending", "finalizing"].includes(viewState) && invitationDetails ? (
				<Card>
					<CardHeader>
						<CardTitle>
							{t("pages.inviteAccept.invitationHeading", {
								circle: invitationDetails.circle?.name,
							})}
						</CardTitle>
					</CardHeader>
					<CardContent className="space-y-4">
						<p className="text-sm text-muted-foreground">
							{invitedBy
								? t("pages.inviteAccept.invitedBy", { inviter: invitedBy })
								: t("pages.inviteAccept.invitedGeneric")}
						</p>
						<div className="flex flex-wrap gap-3">
							<Button
								onClick={handleAccept}
								disabled={mutations.finalizePending}
							>
								{mutations.finalizePending
									? t("pages.inviteAccept.accepting")
									: t("pages.inviteAccept.accept")}
							</Button>
							<Button
								variant="outline"
								onClick={handleDecline}
								disabled={mutations.respondPending}
							>
								{mutations.respondPending
									? t("pages.inviteAccept.declining")
									: t("pages.inviteAccept.decline")}
							</Button>
						</div>
					</CardContent>
				</Card>
			) : null}

			{viewState === "finalizing" ? (
				<StatusMessage variant="info">
					{t("pages.inviteAccept.finalizing")}
				</StatusMessage>
			) : null}

			{viewState === "accepted" ? (
				<Card className="border-success/40 bg-success/10">
					<CardHeader>
						<CardTitle>{t("pages.inviteAccept.acceptedTitle")}</CardTitle>
					</CardHeader>
					<CardContent className="space-y-3 text-sm text-success-foreground">
						<p>
							{t("pages.inviteAccept.acceptedMessage", { circle: circleName })}
						</p>
						<Button
							variant="secondary"
							onClick={() => navigate({ to: "/circles" })}
						>
							{t("pages.inviteAccept.viewCircles")}
						</Button>
					</CardContent>
				</Card>
			) : null}

			{viewState === "declined" ? (
				<StatusMessage variant="info">
					{t("pages.inviteAccept.declinedMessage")}
				</StatusMessage>
			) : null}
		</div>
	);
}

function InvitationAcceptRouteView() {
	const { token } = Route.useSearch();
	return <InvitationAcceptContent token={token} />;
}

export default InvitationAcceptRouteView;
