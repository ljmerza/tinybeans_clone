import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { TFunction } from "i18next";

import type { CircleMemberSummary } from "../types";
import { describeTimestamp } from "../utils/invitationHelpers";

interface MemberActions {
	remove: {
		open: (member: CircleMemberSummary) => void;
		targetId: number | null;
		isPending: boolean;
	};
}

interface CircleMemberListItemProps {
	member: CircleMemberSummary;
	t: TFunction;
	language: string;
	actions: MemberActions;
	currentUserId?: number;
	canRemoveMembers: boolean;
}

export function CircleMemberListItem({
	member,
	t,
	language,
	actions,
	currentUserId,
	canRemoveMembers,
}: CircleMemberListItemProps) {
	const { remove } = actions;

	const joinedAt = describeTimestamp(member.created_at, language);
	const isCurrentUser = currentUserId === member.user.id;
	const isRemoving = remove.targetId === member.membership_id;
	const isOwner = member.is_owner;

	// Owner cannot be removed (by anyone, including themselves)
	const canRemove = !isOwner && (canRemoveMembers && !isCurrentUser);

	return (
		<li className="border border-border rounded-md px-4 py-3 flex flex-col gap-3 transition-colors bg-card/60">
			<div className="flex flex-wrap items-center justify-between gap-2">
				<div className="flex items-center gap-3">
					<div className="font-medium text-sm text-foreground">
						{member.user.display_name || member.user.email}
					</div>
					{member.user.display_name && (
						<span className="text-xs text-muted-foreground">
							{member.user.email}
						</span>
					)}
					{isOwner && (
						<Badge variant="default" className="bg-blue-600 hover:bg-blue-700">
							{t("pages.circles.members.role.owner")}
						</Badge>
					)}
					{member.role === "admin" && !isOwner && (
						<Badge variant="default">
							{t("pages.circles.members.role.admin")}
						</Badge>
					)}
					{isCurrentUser && (
						<Badge variant="accent">
							{t("pages.circles.members.you")}
						</Badge>
					)}
				</div>
				<div className="flex items-center gap-2">
					{canRemove && (
						<Button
							variant="ghost"
							size="sm"
							className="text-destructive hover:text-destructive"
							onClick={() => remove.open(member)}
							disabled={isRemoving || remove.isPending}
						>
							{isRemoving
								? t("pages.circles.members.removing")
								: t("pages.circles.members.remove")}
						</Button>
					)}
					{isOwner && (
						<span className="text-xs text-muted-foreground italic">
							{t("pages.circles.members.cannot_remove_owner")}
						</span>
					)}
				</div>
			</div>

			<div className="text-xs text-muted-foreground space-y-1">
				{joinedAt && (
					<div>{t("pages.circles.members.joined_at", { joinedAt })}</div>
				)}
			</div>
		</li>
	);
}
