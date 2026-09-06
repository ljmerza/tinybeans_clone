/**
 * Query Persistence
 * Persists selected queries (photo-calendar months) to localStorage so they
 * render instantly on revisit while background refetches keep them fresh.
 */

import { createSyncStoragePersister } from "@tanstack/query-sync-storage-persister";
import type { Query } from "@tanstack/react-query";
import type { PersistQueryClientOptions } from "@tanstack/react-query-persist-client";

const PERSIST_KEY = "tinybeans-query-cache";
const PERSIST_BUSTER = "v1";

/**
 * Only queries whose key starts with one of these prefixes are written to
 * localStorage. Everything else (auth, circles, profile) stays memory-only.
 */
const PERSISTED_KEY_PREFIXES: ReadonlyArray<ReadonlyArray<string>> = [
	["keeps", "calendar"],
];

function isPersistedKey(queryKey: readonly unknown[]) {
	return PERSISTED_KEY_PREFIXES.some((prefix) =>
		prefix.every((part, index) => queryKey[index] === part),
	);
}

export function createQueryPersistOptions(): Omit<
	PersistQueryClientOptions,
	"queryClient"
> {
	return {
		persister: createSyncStoragePersister({
			storage: window.localStorage,
			key: PERSIST_KEY,
		}),
		buster: PERSIST_BUSTER,
		maxAge: 1000 * 60 * 60 * 24 * 30, // 30 days
		dehydrateOptions: {
			shouldDehydrateQuery: (query: Query) =>
				query.state.status === "success" && isPersistedKey(query.queryKey),
		},
	};
}
