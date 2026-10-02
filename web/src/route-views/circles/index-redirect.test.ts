import { Route } from "@/routes/circles/index";
import { isRedirect } from "@tanstack/react-router";
import { describe, expect, it } from "vitest";

describe("/circles", () => {
	it("redirects to the Circles settings tab", () => {
		let thrown: unknown;
		try {
			Route.options.beforeLoad?.({} as never);
		} catch (error) {
			thrown = error;
		}

		expect(isRedirect(thrown)).toBe(true);
		expect((thrown as { options: { to: string } }).options.to).toBe(
			"/profile/circles",
		);
	});
});
