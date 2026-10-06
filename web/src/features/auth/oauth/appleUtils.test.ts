import { afterEach, describe, expect, it } from "vitest";
import {
	clearAppleOAuthState,
	getAppleOAuthState,
	getAppleRedirectUri,
	parseAppleCallbackFragment,
	storeAppleOAuthState,
} from "./appleUtils";
import { getOAuthState } from "./utils";

describe("appleUtils", () => {
	afterEach(() => sessionStorage.clear());

	it("parses code and state from the fragment", () => {
		expect(parseAppleCallbackFragment("#code=c.1-2&state=s%2Bx")).toEqual({
			code: "c.1-2",
			state: "s+x",
			error: undefined,
		});
	});

	it("parses an error fragment", () => {
		expect(
			parseAppleCallbackFragment("#error=user_cancelled_authorize&state=s"),
		).toMatchObject({ error: "user_cancelled_authorize", code: undefined });
	});

	it("returns nothing for an empty fragment", () => {
		expect(parseAppleCallbackFragment("")).toEqual({
			code: undefined,
			state: undefined,
			error: undefined,
		});
	});

	it("keeps Apple state separate from Google state", () => {
		storeAppleOAuthState("apple-state");
		expect(getAppleOAuthState()).toBe("apple-state");
		expect(getOAuthState()).toBeNull();
		clearAppleOAuthState();
		expect(getAppleOAuthState()).toBeNull();
	});

	it("points the redirect at the SPA callback route", () => {
		expect(getAppleRedirectUri()).toBe(
			`${window.location.origin}/auth/apple-callback`,
		);
	});
});
