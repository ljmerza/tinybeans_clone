/**
 * Auth Query Keys
 * Centralized factory for TanStack Query auth-related keys.
 */

import { userKeys as profileUserKeys } from "@/features/profile/api/queryKeys";
import { createQueryKeyFactory } from "@/lib/query/queryKeys";

const authKeysFactory = createQueryKeyFactory(["auth"] as const);

export const authKeys = {
	all: () => authKeysFactory.root(),
	session: () => authKeysFactory.tag("session"),
	status: () => authKeysFactory.tag("status"),
};

export const userKeys = profileUserKeys;
