import { describe, expect, it } from "vitest";
import { getRedirectUri } from "./utils";

describe("getRedirectUri", () => {
	it("points Google back at this origin's callback route", () => {
		// Google redirects the browser here, so it has to be the SPA route in
		// routes/auth/google-callback.tsx; anything else lands on a 404 page.
		expect(getRedirectUri()).toBe(
			`${window.location.origin}/auth/google-callback`,
		);
	});
});
