import "@testing-library/jest-dom/vitest";
import { afterAll, afterEach, beforeAll } from "vitest";

import { getMockServer } from "./msw/server";

const server = await getMockServer();

if (server) {
	beforeAll(() => {
		server.listen({ onUnhandledRequest: "error" });
	});

	afterEach(() => {
		server.resetHandlers();
	});

	afterAll(() => {
		server.close();
	});
}
