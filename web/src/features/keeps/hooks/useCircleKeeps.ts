import { useQuery, type UseQueryOptions } from "@tanstack/react-query";

import type { KeepSummary, PaginatedResponse } from "../types";
import { keepsKeys } from "../api/queryKeys";
import { keepsServices } from "../api/services";

function normalizeKeepList(
	response: PaginatedResponse<KeepSummary> | KeepSummary[] | undefined,
): KeepSummary[] {
	if (!response) {
		return [];
	}
	if (Array.isArray(response)) {
		return response;
	}
	if ("results" in response && Array.isArray(response.results)) {
		return response.results;
	}
	return [];
}

export function useCircleKeeps(
	circleId: number | string | undefined,
	options?: UseQueryOptions<
		PaginatedResponse<KeepSummary> | KeepSummary[] | undefined,
		Error,
		KeepSummary[]
	>,
) {
	return useQuery({
		queryKey: keepsKeys.circleMedia(circleId ?? "unknown"),
		queryFn: () =>
			circleId ? keepsServices.listCircleKeeps(circleId, "media") : Promise.resolve(undefined),
		select: normalizeKeepList,
		enabled: circleId != null,
		staleTime: 30_000,
		...options,
	});
}
