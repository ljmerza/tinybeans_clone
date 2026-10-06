import { Button } from "@/components/ui/button";
import {
	type PendingCircleInvitation,
	usePendingInvitations,
	useRespondToCircleInvitation,
} from "@/features/circles";
import { useNavigate } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

interface PendingInvitationsProps {
	/** The list endpoint needs a verified email. */
	enabled: boolean;
}

/**
 * Invitations waiting on the viewer, shown before "create a circle" so an
 * invited relative joins the family circle instead of starting an empty one.
 */
export function PendingInvitations({ enabled }: PendingInvitationsProps) {
	const { t } = useTranslation();
	const navigate = useNavigate();
	const { data: invitations = [] } = usePendingInvitations({ enabled });
	const respond = useRespondToCircleInvitation();

	if (invitations.length === 0) return null;

	const busyId = respond.isPending ? respond.variables?.invitationId : null;

	const accept = (invitation: PendingCircleInvitation) =>
		respond.mutate(
			{ invitationId: invitation.id, action: "accept" },
			{
				onSuccess: (response) => {
					const circleId = response.data?.circle?.id ?? invitation.circle.id;
					navigate({
						to: "/circles/$circleId",
						params: { circleId: String(circleId) },
					});
				},
			},
		);

	return (
		<section className="space-y-3" aria-labelledby="pending-invitations">
			<div className="space-y-1">
				<h2 id="pending-invitations" className="heading-4">
					{t("pages.circleOnboarding.invitationsTitle")}
				</h2>
				<p className="text-sm text-muted-foreground">
					{t("pages.circleOnboarding.invitationsDescription")}
				</p>
			</div>
			<ul className="space-y-2">
				{invitations.map((invitation) => {
					const inviter =
						invitation.invited_by?.display_name ??
						invitation.invited_by?.email ??
						null;
					const busy = busyId === invitation.id;
					return (
						<li
							key={invitation.id}
							className="flex flex-wrap items-center justify-between gap-3 rounded-md border p-3"
						>
							<div className="min-w-0">
								<p className="truncate font-medium">{invitation.circle.name}</p>
								{inviter && (
									<p className="truncate text-xs text-muted-foreground">
										{t("pages.inviteAccept.invitedBy", { inviter })}
									</p>
								)}
							</div>
							<div className="flex gap-2">
								<Button
									variant="ghost"
									size="sm"
									disabled={respond.isPending}
									onClick={() =>
										respond.mutate({
											invitationId: invitation.id,
											action: "decline",
										})
									}
								>
									{busy && respond.variables?.action === "decline"
										? t("pages.inviteAccept.declining")
										: t("pages.inviteAccept.decline")}
								</Button>
								<Button
									size="sm"
									disabled={respond.isPending}
									onClick={() => accept(invitation)}
								>
									{busy && respond.variables?.action === "accept"
										? t("pages.inviteAccept.accepting")
										: t("pages.inviteAccept.accept")}
								</Button>
							</div>
						</li>
					);
				})}
			</ul>
		</section>
	);
}
