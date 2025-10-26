import { useCallback, useMemo, useState } from "react";

import type { CircleMemberSummary } from "../types";
import { useRemoveCircleMember } from "./useCircleInvitationAdmin";
import { useCircleMembers } from "./useCircleMemberships";

export function useCircleMemberListController(circleId: number | string) {
	const membersQuery = useCircleMembers(circleId);
	const removeMember = useRemoveCircleMember(circleId);

	const [removeTarget, setRemoveTarget] = useState<number | null>(null);
	const [removalDialog, setRemovalDialog] = useState<CircleMemberSummary | null>(
		null,
	);

	const members = useMemo(
		() => membersQuery.data?.members ?? [],
		[membersQuery.data],
	);

	const openRemoveDialog = useCallback((member: CircleMemberSummary) => {
		setRemovalDialog(member);
	}, []);

	const handleRemovalDialogOpenChange = useCallback((open: boolean) => {
		if (open) return;
		setRemovalDialog(null);
		setRemoveTarget(null);
	}, []);

	const confirmRemoval = useCallback(async () => {
		if (!removalDialog) {
			return;
		}

		setRemoveTarget(removalDialog.membership_id);
		try {
			await removeMember.mutateAsync(removalDialog.user.id);
			setRemovalDialog(null);
		} finally {
			setRemoveTarget(null);
		}
	}, [removeMember, removalDialog]);

	const cancelRemoval = useCallback(() => {
		setRemovalDialog(null);
		setRemoveTarget(null);
	}, []);

	return {
		members,
		circle: membersQuery.data?.circle,
		query: {
			isFetching: membersQuery.isFetching,
			isLoading: membersQuery.isLoading,
			error: membersQuery.error,
			refetch: membersQuery.refetch,
		},
		removal: {
			dialog: removalDialog,
			open: openRemoveDialog,
			close: handleRemovalDialogOpenChange,
			cancel: cancelRemoval,
			confirm: confirmRemoval,
			targetId: removeTarget,
			isPending: removeMember.isPending,
		},
	};
}
