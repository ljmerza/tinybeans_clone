import { useQuery } from "@tanstack/react-query";

import { circleKeys } from "../api/queryKeys";
import { circleServices } from "../api/services";
import type { PendingCircleInvitation } from "../types";

/** Invitations waiting on the viewer. The API needs a verified email. */
export function usePendingInvitations({ enabled }: { enabled: boolean }) {
	return useQuery({
		queryKey: circleKeys.pendingInvitations(),
		queryFn: async () => {
			const response = await circleServices.listPendingInvitations();
			const payload = response.data ?? response;
			return (
				(payload as { invitations?: PendingCircleInvitation[] }).invitations ??
				[]
			);
		},
		enabled,
	});
}
