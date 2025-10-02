import { showApiToast, extractMessage } from "@/lib/toast";
import { authStore, setAccessToken } from "./store";

export const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

// Get CSRF token from cookie
function getCsrfToken(): string | null {
	const name = "csrftoken";
	const value = `; ${document.cookie}`;
	const parts = value.split(`; ${name}=`);
	if (parts.length === 2) return parts.pop()?.split(";").shift() || null;
	return null;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
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
			return request<T>(path, init);
		}
	}

	if (!res.ok) {
		showApiToast(data, res.status, { fallbackMessage: res.statusText });
		const message = extractMessage(data) ?? res.statusText;
		throw Object.assign(new Error(message), {
			status: res.status,
			data,
		});
	}

	showApiToast(data, res.status);
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
	if (!res.ok) return false;
	const data = (await res.json().catch(() => null)) as any;
	if (data?.access) {
		setAccessToken(data.access);
		return true;
	}
	return false;
}

export const api = {
	get: <T>(path: string) => request<T>(path),
	post: <T>(path: string, body?: any) =>
		request<T>(path, {
			method: "POST",
			body: body ? JSON.stringify(body) : undefined,
		}),
	patch: <T>(path: string, body?: any) =>
		request<T>(path, {
			method: "PATCH",
			body: body ? JSON.stringify(body) : undefined,
		}),
	delete: <T>(path: string, body?: any) =>
		request<T>(path, {
			method: "DELETE",
			body: body ? JSON.stringify(body) : undefined,
		}),
};
