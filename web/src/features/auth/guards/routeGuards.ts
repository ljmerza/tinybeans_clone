/**
 * Route Guards
 * Utilities for protecting routes using TanStack Router's beforeLoad hook
 */

import type { HttpError } from "@/lib/httpClient";
import type { QueryClient } from "@tanstack/react-query";
import { redirect } from "@tanstack/react-router";
import { authKeys } from "../api/queryKeys";
import { authServices } from "../api/services";
import { authStore, setAccessToken } from "../store/authStore";
import type { AuthUser, MeResponse } from "../types";

interface GuardContext {
	queryClient?: QueryClient;
}

async function resolveSessionUser(queryClient?: QueryClient) {
	if (!queryClient) {
		return null;
	}

	// Avoid triggering session fetch (and token refresh attempts) when user is a guest.
	const { accessToken } = authStore.state;
	if (!accessToken) {
		return null;
	}

	const cached = queryClient.getQueryData<AuthUser>(authKeys.session());
	if (cached) {
		return cached;
	}

	try {
		const user = await queryClient.fetchQuery({
			queryKey: authKeys.session(),
			queryFn: async () => {
				const response = await authServices.getSession({
					suppressErrorToast: true,
				});
				const data = (response.data ?? response) as MeResponse;
				return data.user;
			},
			staleTime: 1000 * 60,
		});
		return user;
	} catch (error) {
		const httpError = error as HttpError | undefined;
		if (httpError?.status === 401) {
			setAccessToken(null);
		}
		return null;
	}
}

/**
 * Guard that requires authentication
 * Use in route's beforeLoad to protect authenticated-only pages
 *
 * @example
 * export const Route = createFileRoute('/dashboard')({
 *   beforeLoad: requireAuth,
 *   component: DashboardPage,
 * })
 */
export async function requireAuth({
	context,
}: {
	context: GuardContext;
}) {
	const { accessToken } = authStore.state;
	const user = await resolveSessionUser(context.queryClient);

	if (!user && !accessToken) {
		throw redirect({
			to: "/login",
			search: {
				redirect: window.location.pathname,
			},
		});
	}
}

/**
 * Guard that requires guest (not authenticated)
 * Use in route's beforeLoad to redirect authenticated users away from public-only pages
 *
 * @example
 * export const Route = createFileRoute('/login')({
 *   beforeLoad: requireGuest,
 *   component: LoginPage,
 * })
 */
export async function requireGuest({
	context,
}: {
	context: GuardContext;
}) {
	const { accessToken } = authStore.state;
	const user = await resolveSessionUser(context.queryClient);

	if (user || accessToken) {
		throw redirect({
			to: "/",
		});
	}
}

export async function requireCircleOnboardingComplete({
	context,
}: {
	context: GuardContext;
}) {
	const user = await resolveSessionUser(context.queryClient);
	if (user?.needs_circle_onboarding) {
		throw redirect({
			to: "/circles/onboarding",
		});
	}
}

export async function requireCircleOnboardingIncomplete({
	context,
}: {
	context: GuardContext;
}) {
	const user = await resolveSessionUser(context.queryClient);
	if (!user?.needs_circle_onboarding) {
		throw redirect({
			to: "/",
		});
	}
}

/**
 * Create a custom auth guard with specific redirect
 *
 * @example
 * const requireAdmin = createAuthGuard({
 *   checkAuth: () => isAdmin(),
 *   redirectTo: '/403',
 * })
 */
export function createAuthGuard(options: {
	checkAuth: () => boolean;
	redirectTo: string;
	redirectSearch?: Record<string, unknown>;
}) {
	return () => {
		if (!options.checkAuth()) {
			throw redirect({
				to: options.redirectTo,
				search: options.redirectSearch,
			});
		}
	};
}
