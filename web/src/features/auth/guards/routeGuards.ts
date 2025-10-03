/**
 * Route Guards
 * Utilities for protecting routes using TanStack Router's beforeLoad hook
 */

import { redirect } from "@tanstack/react-router";
import { authStore } from "../store/authStore";

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
export function requireAuth() {
	const { accessToken } = authStore.state;

	if (!accessToken) {
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
export function requireGuest() {
	const { accessToken } = authStore.state;

	if (accessToken) {
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
