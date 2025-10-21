/**
 * Auth Query Keys
 * Centralized factory for TanStack Query auth-related keys.
 */

import { userKeys as profileUserKeys } from "@/features/profile/api/queryKeys";
import type { QueryKey } from "@tanstack/react-query";
import { createQueryKeyFactory } from "@/lib/query/queryKeys";

const authKeysFactory = createQueryKeyFactory(["auth"] as const);

const mutationKey = <Parts extends QueryKey>(...parts: Parts) =>
	authKeysFactory.tag("mutation", ...parts);

export const authKeys = {
	all: () => authKeysFactory.root(),
	session: () => authKeysFactory.tag("session"),
	status: () => authKeysFactory.tag("status"),
	mutation: mutationKey,
	mutations: {
		login: () => mutationKey("login"),
		signup: () => mutationKey("signup"),
		resendVerification: () => mutationKey("resend-verification"),
		verifyEmail: () => mutationKey("verify-email"),
		refreshToken: () => mutationKey("refresh-token"),
	},
};

export const userKeys = profileUserKeys;
