import type { SetupServerApi } from "msw/node";
import { handlers } from "./handlers";

type MockServer = SetupServerApi;

let serverPromise: Promise<MockServer | null> | null = null;

async function createServer(): Promise<MockServer | null> {
	try {
		const { setupServer } = await import("msw/node");
		return setupServer(...handlers);
	} catch (error) {
		if (process.env.NODE_ENV === "test") {
			console.warn(
				"[test-utils] MSW not installed; HTTP requests will hit the real network.",
			);
			if (process.env.MSW_DEBUG) {
				console.error(error);
			}
		}
		return null;
	}
}

export async function getMockServer(): Promise<MockServer | null> {
	if (!serverPromise) {
		serverPromise = createServer();
	}
	return serverPromise;
}
