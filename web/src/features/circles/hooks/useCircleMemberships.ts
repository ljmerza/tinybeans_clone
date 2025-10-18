import type { ApiResponseWithMessages } from "@/types";
import { useQuery } from "@tanstack/react-query";

import { circleKeys } from "../api/queryKeys";
import { circleServices } from "../api/services";
import type {
	CircleMemberSummary,
	CircleMembershipSummary,
	CircleSummary,
} from "../types";

function extractMemberships(
	response: ApiResponseWithMessages<{ circles: CircleMembershipSummary[] }>,
) {
	if ("data" in response && response.data) {
		return response.data.circles;
	}
	return response.circles;
}

export function useCircleMemberships() {
	return useQuery({
		queryKey: circleKeys.list(),
		queryFn: async () => {
			const response = await circleServices.listMemberships();
			return extractMemberships(response);
		},
	});
}

export interface CircleMembersPayload {
	circle: CircleSummary;
	members: CircleMemberSummary[];
}

export function useCircleMembers(circleId: number | string) {
	return useQuery<CircleMembersPayload>({
		queryKey: circleKeys.members(circleId),
		queryFn: async () => {
			const response = await circleServices.getCircleMembers(circleId);
			if ("data" in response && response.data) {
				return response.data as CircleMembersPayload;
			}
			return response as unknown as CircleMembersPayload;
		},
	});
}
