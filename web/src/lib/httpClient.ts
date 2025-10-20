/**
 * @deprecated Use modules in `@/lib/api/client` directly.
 * This file re-exports the new client for backwards compatibility.
 */

export {
	API_BASE,
	createApiClient,
	createHttpClient,
	createHttpError,
	getCsrfToken,
	httpRequest,
	type ApiClientOptions,
	type ApiMessage,
	type ApiResponse,
	type HttpError,
	type RequestOptions,
} from "./api/client";
