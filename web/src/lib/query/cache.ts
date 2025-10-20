/**
 * Query Cache Helpers
 * Utility functions for reading and writing TanStack Query cache entries.
 */

import type { QueryClient, QueryKey, Updater } from "@tanstack/react-query";

/**
 * Safely update cached query data with type inference.
 */
export function updateCachedQuery<TData>(
	queryClient: QueryClient,
	queryKey: QueryKey,
	updater: Updater<TData | undefined, TData | undefined>,
) {
	queryClient.setQueryData(queryKey, updater);
}

/**
 * Retrieve cached query data with optional fallback.
 */
export function getCachedQuery<TData>(
	queryClient: QueryClient,
	queryKey: QueryKey,
	defaultValue?: TData,
) {
	const data = queryClient.getQueryData<TData>(queryKey);
	return data ?? defaultValue;
}
