declare module "msw" {
	// Minimal placeholder; the real package provides richer types.
	export type RequestHandler = unknown;
}

declare module "msw/node" {
	import type { RequestHandler } from "msw";

	export interface SetupServerApi {
		listen: (options?: {
			onUnhandledRequest?: "error" | "warn" | "bypass";
		}) => void;
		close: () => void;
		resetHandlers: (...handlers: RequestHandler[]) => void;
		use: (...handlers: RequestHandler[]) => void;
	}

	export function setupServer(...handlers: RequestHandler[]): SetupServerApi;
}
