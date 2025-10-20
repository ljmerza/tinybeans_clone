/**
 * API Client
 * Centralized wrapper around `fetch` for React Query usage.
 * Handles CSRF, auth headers, response parsing, and structured errors.
 */

import type { ApiMessage, ApiResponse } from "@/types";

export type { ApiMessage, ApiResponse };

export const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

export interface RequestOptions {
	suppressSuccessToast?: boolean;
	suppressErrorToast?: boolean;
}

export interface HttpError extends Error {
	status: number;
	data: unknown;
	messages?: ApiMessage[];
}

export interface ApiClientOptions extends RequestOptions {
	getAuthToken?: () => string | null;
	onUnauthorized?: () => Promise<boolean>;
	onSuccess?: (data: unknown, status: number) => void;
	onError?: (data: unknown, status: number, fallbackMessage: string) => void;
	skipRetryPaths?: string[];
}

/**
 * Get CSRF token from cookies.
 */
export function getCsrfToken(): string | null {
	const name = "csrftoken";
	const value = `; ${document.cookie}`;
	const parts = value.split(`; ${name}=`);
	if (parts.length === 2) return parts.pop()?.split(";").shift() || null;
	return null;
}

/**
 * Create structured HTTP error.
 */
export function createHttpError(
	message: string,
	status: number,
	data: unknown,
	messages?: ApiMessage[],
): HttpError {
	const error = new Error(message) as HttpError;
	error.status = status;
	error.data = data;
	if (messages) {
		error.messages = messages;
	}
	return error;
}

/**
 * Base request primitive used by all API clients.
 */
export async function httpRequest<T>(
	path: string,
	init: RequestInit = {},
	options: ApiClientOptions = {},
): Promise<T> {
	const headers = new Headers(init.headers);

	if (
		!headers.has("Content-Type") &&
		init.body &&
		!(init.body instanceof FormData)
	) {
		headers.set("Content-Type", "application/json");
	}

	if (init.method && init.method !== "GET") {
		const csrfToken = getCsrfToken();
		if (csrfToken) {
			headers.set("X-CSRFToken", csrfToken);
		}
	}

	if (options.getAuthToken) {
		const token = options.getAuthToken();
		if (token) {
			headers.set("Authorization", `Bearer ${token}`);
		}
	}

	const response = await fetch(`${API_BASE}${path}`, {
		credentials: "include",
		...init,
		headers,
	});

	const rawBody = await response.text().catch(() => "");
	let data: unknown = undefined;
	if (rawBody) {
		try {
			data = JSON.parse(rawBody);
		} catch {
			data = rawBody;
		}
	}

	const skipRetry = options.skipRetryPaths?.includes(path);
	if (response.status === 401 && !skipRetry && options.onUnauthorized) {
		const refreshed = await options.onUnauthorized();
		if (refreshed) {
			return httpRequest<T>(path, init, options);
		}
	}

	if (!response.ok) {
		if (options.onError && !options.suppressErrorToast) {
			options.onError(data, response.status, response.statusText);
		}

		const messages = extractMessages(data);
		const message = extractLegacyMessage(data) ?? response.statusText;
		throw createHttpError(message, response.status, data, messages);
	}

	if (options.onSuccess && !options.suppressSuccessToast) {
		options.onSuccess(data, response.status);
	}

	return data as T;
}

/**
 * Simple HTTP client abstraction for feature services.
 */
export function createApiClient(baseOptions: ApiClientOptions = {}) {
	return {
		request: <TResponse>(
			path: string,
			init?: RequestInit,
			options?: RequestOptions,
		) => httpRequest<TResponse>(path, init, { ...baseOptions, ...options }),

		get: <TResponse>(path: string, options?: RequestOptions) =>
			httpRequest<TResponse>(path, {}, { ...baseOptions, ...options }),

		post: <TResponse, TBody = unknown>(
			path: string,
			body?: TBody,
			options?: RequestOptions,
		) =>
			httpRequest<TResponse>(
				path,
				{
					method: "POST",
					body: body === undefined ? undefined : JSON.stringify(body),
				},
				{ ...baseOptions, ...options },
			),

		patch: <TResponse, TBody = unknown>(
			path: string,
			body?: TBody,
			options?: RequestOptions,
		) =>
			httpRequest<TResponse>(
				path,
				{
					method: "PATCH",
					body: body === undefined ? undefined : JSON.stringify(body),
				},
				{ ...baseOptions, ...options },
			),

		delete: <TResponse, TBody = unknown>(
			path: string,
			body?: TBody,
			options?: RequestOptions,
		) =>
			httpRequest<TResponse>(
				path,
				{
					method: "DELETE",
					body: body === undefined ? undefined : JSON.stringify(body),
				},
				{ ...baseOptions, ...options },
			),
	};
}

/**
 * Extract messages array from structured response.
 */
function extractMessages(data: unknown): ApiMessage[] | undefined {
	if (!data || typeof data !== "object") return undefined;
	const obj = data as Record<string, unknown>;

	if (Array.isArray(obj.messages)) {
		return obj.messages.filter(
			(msg): msg is ApiMessage =>
				typeof msg === "object" &&
				msg !== null &&
				"i18n_key" in msg &&
				typeof msg.i18n_key === "string",
		);
	}

	return undefined;
}

/**
 * Extract error message from legacy API response format.
 * @deprecated Prefer messages with i18n keys.
 */
function extractLegacyMessage(data: unknown): string | null {
	if (!data || typeof data !== "object") return null;

	const obj = data as Record<string, unknown>;

	if (typeof obj.detail === "string") return obj.detail;
	if (typeof obj.message === "string") return obj.message;
	if (typeof obj.error === "string") return obj.error;

	if (Array.isArray(obj.detail)) {
		return obj.detail.join(", ");
	}
	if (Array.isArray(obj.errors)) {
		return obj.errors.join(", ");
	}

	if (typeof obj.non_field_errors !== "undefined") {
		const nfe = obj.non_field_errors;
		if (Array.isArray(nfe)) return nfe.join(", ");
		if (typeof nfe === "string") return nfe;
	}

	return null;
}

/**
 * Alias for legacy imports until all modules migrate.
 */
export const createHttpClient = createApiClient;
