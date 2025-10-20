/**
 * Query Key Utilities
 * Provides helpers for creating scoped TanStack Query keys.
 */

import type { QueryKey } from "@tanstack/react-query";

export type QueryKeyFactory<Root extends QueryKey> = {
	root: () => Root;
	tag: <Parts extends QueryKey>(...parts: Parts) => [...Root, ...Parts];
	entity: <Id>(id: Id) => [...Root, Id];
};

/**
 * Create a query key factory for a domain namespace.
 */
export function createQueryKeyFactory<const Root extends QueryKey>(
	rootKey: Root,
): QueryKeyFactory<Root> {
	const root = rootKey;

	const append = <Parts extends QueryKey>(...parts: Parts) =>
		[...root, ...parts] as [...Root, ...Parts];

	return {
		root: () => root,
		tag: append,
		entity: <Id>(id: Id) => append(id),
	};
}
