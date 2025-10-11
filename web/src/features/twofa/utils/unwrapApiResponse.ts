/**
 * Normalize API responses that may wrap payloads in a `data` key.
 */
export function unwrapApiResponse<T>(response: unknown): T | undefined {
	if (!response || typeof response !== "object") {
		return response as T | undefined;
	}

	const payload = response as { data?: T };
	if (payload.data !== undefined) {
		return payload.data;
	}

	return response as T;
}
