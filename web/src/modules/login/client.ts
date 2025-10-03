import { extractMessage, showApiToast } from "@/lib/toast";
import { authStore, setAccessToken } from "./store";
import type { RefreshAccessTokenResponse } from "./types";

export const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

type RequestOptions = {
	suppressSuccessToast?: boolean;
	suppressErrorToast?: boolean;
};

// Get CSRF token from cookie
function getCsrfToken(): string | null {
	const name = "csrftoken";
	const value = `; ${document.cookie}`;
	const parts = value.split(`; ${name}=`);
	if (parts.length === 2) return parts.pop()?.split(";").shift() || null;
	return null;
}

async function request<T>(
	path: string,
	init: RequestInit = {},
	options: RequestOptions = {},
): Promise<T> {
	const headers = new Headers(init.headers);
	if (
		!headers.has("Content-Type") &&
		init.body &&
		!(init.body instanceof FormData)
	) {
		headers.set("Content-Type", "application/json");
	}

	// Add CSRF token for non-GET requests
	if (init.method && init.method !== "GET") {
		const csrfToken = getCsrfToken();
		console.log(
			"CSRF Token:",
			csrfToken ? "Found" : "NOT FOUND",
			"| Cookie:",
			document.cookie.substring(0, 100),
		);
		if (csrfToken) {
			headers.set("X-CSRFToken", csrfToken);
			console.log("Added X-CSRFToken header");
		} else {
			console.warn("⚠️ No CSRF token found! Check if /auth/csrf/ was called");
		}
	}

	const token = authStore.state.accessToken;
	if (token) headers.set("Authorization", `Bearer ${token}`);
	const res = await fetch(`${API_BASE}${path}`, {
		credentials: "include",
		...init,
		headers,
	});

	const rawBody = await res.text().catch(() => "");
	let data: unknown = undefined;
	if (rawBody) {
		try {
			data = JSON.parse(rawBody);
		} catch (error) {
			data = rawBody;
		}
	}

	// Don't retry on 401 for login, signup, or token refresh endpoints
	const skipRetry =
		path === "/auth/login/" ||
		path === "/auth/signup/" ||
		path === "/auth/token/refresh/";
	if (res.status === 401 && !skipRetry) {
		const refreshed = await refreshAccessToken();
		if (refreshed) {
			return request<T>(path, init, options);
		}
	}

	if (!res.ok) {
		if (!options.suppressErrorToast) {
			showApiToast(data, res.status, { fallbackMessage: res.statusText });
		}
		const message = extractMessage(data) ?? res.statusText;
		throw Object.assign(new Error(message), {
			status: res.status,
			data,
		});
	}

	if (!options.suppressSuccessToast) {
		showApiToast(data, res.status);
	}
	return data as T;
}

export async function refreshAccessToken(): Promise<boolean> {
	const csrfToken = getCsrfToken();
	const headers: HeadersInit = { "Content-Type": "application/json" };
	if (csrfToken) headers["X-CSRFToken"] = csrfToken;

	const res = await fetch(`${API_BASE}/auth/token/refresh/`, {
		method: "POST",
		credentials: "include",
		headers,
	});
	if (!res.ok) {
		// Clear the access token when refresh fails to log out the user
		setAccessToken(null);
		return false;
	}
	const data: RefreshAccessTokenResponse | null = await res
		.json()
		.catch(() => null);
	if (data?.access) {
		setAccessToken(data.access);
		return true;
	}
	// Clear token if response doesn't contain access token
	setAccessToken(null);
	return false;
}

export const api = {
	get: <TResponse>(path: string, options?: RequestOptions) =>
		request<TResponse>(path, {}, options),
	post: <TResponse, TBody = unknown>(
		path: string,
		body?: TBody,
		options?: RequestOptions,
	) =>
		request<TResponse>(
			path,
			{
				method: "POST",
				body: body === undefined ? undefined : JSON.stringify(body),
			},
			options,
		),
	patch: <TResponse, TBody = unknown>(
		path: string,
		body?: TBody,
		options?: RequestOptions,
	) =>
		request<TResponse>(
			path,
			{
				method: "PATCH",
				body: body === undefined ? undefined : JSON.stringify(body),
			},
			options,
		),
	delete: <TResponse, TBody = unknown>(
		path: string,
		body?: TBody,
		options?: RequestOptions,
	) =>
		request<TResponse>(
			path,
			{
				method: "DELETE",
				body: body === undefined ? undefined : JSON.stringify(body),
			},
			options,
		),
};

export type { RequestOptions };
