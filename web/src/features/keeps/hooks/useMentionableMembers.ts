import { useQuery } from "@tanstack/react-query";

import { keepKeys } from "../api/queryKeys";
import { keepServices } from "../api/services";

/**
 * Members the viewer can @mention in a circle's comments (everyone but the
 * viewer), in name order. Fetched once `enabled`, i.e. when a mention starts.
 */
export function useMentionableMembers(circleId: number, enabled: boolean) {
	return useQuery({
		queryKey: keepKeys.mentionable(circleId),
		queryFn: () => keepServices.getMentionableMembers(circleId),
		enabled,
	});
}
