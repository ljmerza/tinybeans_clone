import { showToast } from "@/lib/toast";
import { useCallback, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import type { CircleInvitationSummary } from "../types";
import {
	findMemberId,
	normalizeId,
	sortInvitations,
} from "../utils/invitationHelpers";
import {
	useCancelCircleInvitation,
	useCircleInvitationsQuery,
	useRemoveCircleMember,
	useResendCircleInvitation,
} from "./useCircleInvitationAdmin";
import { useCircleMembers } from "./useCircleMemberships";

interface RemovalDialogState {
	invitation: CircleInvitationSummary;
	memberId?: string;
}

export function useCircleInvitationListController(circleId: number | string) {
	const { t } = useTranslation();

	const invitationsQuery = useCircleInvitationsQuery(circleId);
	const resendInvitation = useResendCircleInvitation(circleId);
	const cancelInvitation = useCancelCircleInvitation(circleId);
	const removeMember = useRemoveCircleMember(circleId);
	const membersQuery = useCircleMembers(circleId);

	const [resendTarget, setResendTarget] = useState<string | null>(null);
	const [cancelTarget, setCancelTarget] = useState<string | null>(null);
	const [confirmingId, setConfirmingId] = useState<string | null>(null);
	const [removeTarget, setRemoveTarget] = useState<string | null>(null);
	const [removalDialog, setRemovalDialog] = useState<RemovalDialogState | null>(
		null,
	);
	const [resolvingMemberFor, setResolvingMemberFor] = useState<string | null>(
		null,
	);
	const confirmingRemovalRef = useRef(false);

	const invitations = useMemo(
		() => sortInvitations(invitationsQuery.data),
		[invitationsQuery.data],
	);

	const resolveMemberId = useCallback(
		(invitation: CircleInvitationSummary) =>
			findMemberId(invitation, membersQuery.data?.members),
		[membersQuery.data],
	);

	const ensureMemberId = useCallback(
		async (invitation: CircleInvitationSummary) => {
			const existing = resolveMemberId(invitation);
			if (existing) {
				return existing;
			}

			const refreshed = await membersQuery.refetch();
			return findMemberId(invitation, refreshed.data?.members);
		},
		[membersQuery, resolveMemberId],
	);

	const handleResend = useCallback(
		async (invitationId: string) => {
			setResendTarget(invitationId);
			try {
				await resendInvitation.mutateAsync(invitationId);
			} finally {
				setResendTarget(null);
			}
		},
		[resendInvitation],
	);

	const handleCancel = useCallback(
		async (invitationId: string) => {
			setCancelTarget(invitationId);
			try {
				await cancelInvitation.mutateAsync(invitationId);
			} finally {
				setCancelTarget(null);
				setConfirmingId(null);
			}
		},
		[cancelInvitation],
	);

	const handleCancelDialogOpenChange = useCallback((open: boolean) => {
		if (open) return;
		setConfirmingId(null);
		setCancelTarget(null);
	}, []);

	const openRemoveDialog = useCallback(
		(invitation: CircleInvitationSummary) => {
			const initialMemberId =
				resolveMemberId(invitation) ??
				normalizeId(invitation.invited_user?.id) ??
				normalizeId(invitation.invited_user_id) ??
				undefined;

			setRemovalDialog({
				invitation,
				memberId: initialMemberId,
			});

			if (initialMemberId) {
				return;
			}

			setResolvingMemberFor(invitation.id);
			void ensureMemberId(invitation)
				.then((resolvedId) => {
					if (!resolvedId) {
						return;
					}
					setRemovalDialog((current) =>
						current && current.invitation.id === invitation.id
							? { ...current, memberId: resolvedId }
							: current,
					);
				})
				.finally(() => {
					setResolvingMemberFor(null);
				});
		},
		[ensureMemberId, resolveMemberId],
	);

	const handleRemovalDialogOpenChange = useCallback((open: boolean) => {
		if (open) return;
		if (confirmingRemovalRef.current) {
			return;
		}
		setRemovalDialog(null);
		setRemoveTarget(null);
	}, []);

	const confirmRemoval = useCallback(async () => {
		if (!removalDialog) {
			return;
		}

		const { invitation } = removalDialog;
		confirmingRemovalRef.current = true;

		try {
			let memberId =
				normalizeId(removalDialog.memberId) ??
				normalizeId(invitation.invited_user?.id) ??
				normalizeId(invitation.invited_user_id);

			if (!memberId) {
				setResolvingMemberFor(invitation.id);
				try {
					memberId = await ensureMemberId(invitation);
				} finally {
					setResolvingMemberFor(null);
				}
			}

			if (!memberId) {
				showToast({
					message: t("pages.circles.invites.list.remove_error"),
					level: "error",
				});
				return;
			}

			setRemovalDialog({ invitation, memberId });
			setRemoveTarget(invitation.id);
			await removeMember.mutateAsync(memberId);
			setRemovalDialog(null);
		} finally {
			confirmingRemovalRef.current = false;
			setRemoveTarget(null);
		}
	}, [ensureMemberId, removeMember, removalDialog, t]);

	const cancelRemoval = useCallback(() => {
		setRemovalDialog(null);
		setRemoveTarget(null);
	}, []);

	const confirmCancel = useCallback(async () => {
		if (!confirmingId) {
			return;
		}
		await handleCancel(confirmingId);
	}, [confirmingId, handleCancel]);

	return {
		invitations,
		query: {
			isFetching: invitationsQuery.isFetching,
			isLoading: invitationsQuery.isLoading,
			error: invitationsQuery.error,
			refetch: invitationsQuery.refetch,
		},
		resend: {
			trigger: handleResend,
			targetId: resendTarget,
			isPending: resendInvitation.isPending,
		},
		cancel: {
			open: setConfirmingId,
			close: handleCancelDialogOpenChange,
			confirm: confirmCancel,
			confirmId: confirmingId,
			targetId: cancelTarget,
			isPending: cancelInvitation.isPending,
		},
		removal: {
			dialog: removalDialog,
			open: openRemoveDialog,
			close: handleRemovalDialogOpenChange,
			cancel: cancelRemoval,
			confirm: confirmRemoval,
			targetId: removeTarget,
			isPending: removeMember.isPending,
			resolvingId: resolvingMemberFor,
		},
	};
}
