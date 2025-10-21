import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { TFunction } from "i18next";

import type { CircleInvitationStatus, CircleInvitationSummary } from "../types";
import { describeTimestamp } from "../utils/invitationHelpers";

interface InvitationActions {
	resend: {
		trigger: (invitationId: string) => Promise<void> | void;
		targetId: string | null;
		isPending: boolean;
	};
	cancel: {
		open: (invitationId: string) => void;
		targetId: string | null;
		isPending: boolean;
	};
	removal: {
		open: (invitation: CircleInvitationSummary) => void;
		targetId: string | null;
		isPending: boolean;
		resolvingId: string | null;
	};
}

interface CircleInvitationListItemProps {
	invitation: CircleInvitationSummary;
	t: TFunction;
	language: string;
	actions: InvitationActions;
}

const STATUS_VARIANTS: Record<
	CircleInvitationStatus,
	"default" | "success" | "warning" | "destructive"
> = {
	pending: "default",
	accepted: "success",
	declined: "destructive",
	cancelled: "destructive",
	expired: "warning",
};

export function CircleInvitationListItem({
	invitation,
	t,
	language,
	actions,
}: CircleInvitationListItemProps) {
	const { resend, cancel, removal } = actions;

	const statusVariant = STATUS_VARIANTS[invitation.status];
	const createdAt = describeTimestamp(invitation.created_at, language);
	const respondedAt = describeTimestamp(invitation.responded_at, language);

	const isPending = invitation.status === "pending";
	const isResending = resend.targetId === invitation.id;
	const isCancelling = cancel.targetId === invitation.id;
	const canRemove = invitation.status === "accepted";
	const isRemoving =
		removal.targetId === invitation.id && removal.isPending;
	const isResolving = removal.resolvingId === invitation.id;
	const disableRemove =
		isResolving || (removal.isPending && !isRemoving);

	return (
		<li className="border border-border rounded-md px-4 py-3 flex flex-col gap-3 transition-colors bg-card/60">
			<div className="flex flex-wrap items-center justify-between gap-2">
				<div className="flex items-center gap-3">
					<div className="font-medium text-sm text-foreground">
						{invitation.email}
					</div>
					<Badge variant={statusVariant}>
						{t(
							`pages.circles.invites.status.${invitation.status as CircleInvitationStatus}`,
						)}
					</Badge>
					{invitation.existing_user ? (
						<Badge variant="accent">
							{t("pages.circles.invites.list.existing_user")}
						</Badge>
					) : null}
				</div>
				<div className="flex items-center gap-2">
					{isPending ? (
						<>
							<Button
								variant="ghost"
								size="sm"
								onClick={() => void resend.trigger(invitation.id)}
								disabled={isResending || isCancelling}
							>
								{isResending
									? t("pages.circles.invites.list.resending")
									: t("pages.circles.invites.list.resend")}
							</Button>
							<Button
								variant="ghost"
								size="sm"
								className="text-destructive hover:text-destructive"
								onClick={() => cancel.open(invitation.id)}
								disabled={isCancelling || isResending}
							>
								{isCancelling
									? t("pages.circles.invites.list.cancelling")
									: t("pages.circles.invites.list.cancel")}
							</Button>
						</>
					) : null}
					{canRemove ? (
						<Button
							variant="ghost"
							size="sm"
							className="text-destructive hover:text-destructive"
							onClick={() => removal.open(invitation)}
							disabled={disableRemove}
						>
							{isRemoving
								? t("pages.circles.invites.list.removing")
								: t("pages.circles.invites.list.remove")}
						</Button>
					) : null}
				</div>
			</div>

			<div className="text-xs text-muted-foreground space-y-1">
				{createdAt ? (
					<div>
						{t("pages.circles.invites.list.created_at", { createdAt })}
					</div>
				) : null}
				{respondedAt ? (
					<div>
						{t("pages.circles.invites.list.responded_at", { respondedAt })}
					</div>
				) : null}
				{invitation.reminder_sent_at ? (
					<div>
						{t("pages.circles.invites.list.reminder_sent_at", {
							reminderAt: describeTimestamp(
								invitation.reminder_sent_at,
								language,
							),
						})}
					</div>
				) : null}
			</div>
		</li>
	);
}
