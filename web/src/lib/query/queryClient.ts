/**
 * Query Client Factory
 * Provides shared configuration for TanStack Query usage across the app.
 */

import {
	type DefaultOptions,
	QueryClient,
	type QueryClientConfig,
} from "@tanstack/react-query";
import { createMutationCache } from "./mutationCache";

/**
 * Base query client options tuned for the Tinybeans frontend.
 */
export const defaultQueryClientOptions: DefaultOptions = {
	queries: {
		staleTime: 1000 * 60 * 5, // 5 minutes
		gcTime: 1000 * 60 * 30, // 30 minutes
		retry: false,
		refetchOnWindowFocus: false,
		refetchOnReconnect: true,
	},
	mutations: {
		retry: false,
	},
};

/**
 * Create a QueryClient with shared defaults.
 */
export function createQueryClient(config: QueryClientConfig = {}) {
	return new QueryClient({
		mutationCache: config.mutationCache ?? createMutationCache(),
		...config,
		defaultOptions: {
			queries: {
				...defaultQueryClientOptions.queries,
				...config.defaultOptions?.queries,
			},
			mutations: {
				...defaultQueryClientOptions.mutations,
				...config.defaultOptions?.mutations,
			},
		},
	});
}

/**
 * Convenience helper for tests to avoid memory leaks between cases.
 */
export function createTestQueryClient(config: QueryClientConfig = {}) {
	return createQueryClient({
		...config,
		defaultOptions: {
			queries: {
				...defaultQueryClientOptions.queries,
				gcTime: 0,
				retry: false,
				...config.defaultOptions?.queries,
			},
			mutations: {
				...defaultQueryClientOptions.mutations,
				retry: false,
				...config.defaultOptions?.mutations,
			},
		},
	});
}
