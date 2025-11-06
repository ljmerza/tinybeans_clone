import { useQuery, type UseQueryOptions } from "@tanstack/react-query";

import { keepsKeys } from "../api/queryKeys";
import { keepsServices } from "../api/services";
import type { KeepDetail } from "../types";

export function useKeepDetail(
	keepId: string | undefined,
	options?: UseQueryOptions<KeepDetail | undefined, Error, KeepDetail | undefined>,
) {
	return useQuery({
		queryKey: keepsKeys.detail(keepId ?? "unknown"),
		queryFn: () =>
			keepId ? keepsServices.getKeep(keepId) : Promise.resolve(undefined),
		enabled: Boolean(keepId),
		staleTime: 10_000,
		...options,
	});
}
