import { beforeEach, describe, expect, it, vi } from "vitest";

const post = vi.fn();
const del = vi.fn();

vi.mock("../api/authClient", () => ({
	apiClient: {
		post: (...args: unknown[]) => post(...args),
		delete: (...args: unknown[]) => del(...args),
	},
}));

import { oauthApi, unwrapOAuthResponse } from "./client";
import type { OAuthInitiateResponse } from "./types";

describe("oauthApi", () => {
	beforeEach(() => {
		post.mockReset();
		del.mockReset();
	});

	it("initiate returns the Google URL from the {data} envelope", async () => {
		post.mockResolvedValue({
			data: {
				google_oauth_url: "https://accounts.google.com/o/oauth2/v2/auth?x=1",
				state: "s",
				expires_in: 600,
			},
		});

		const result = await oauthApi.initiate({
			redirect_uri: "https://circles.example.com/auth/google-callback",
		});

		expect(result.google_oauth_url).toBe(
			"https://accounts.google.com/o/oauth2/v2/auth?x=1",
		);
	});

	it("callback exposes tokens and keeps top-level messages", async () => {
		const messages = [{ i18n_key: "notifications.auth.welcome" }];
		post.mockResolvedValue({
			data: { user: { id: 1 }, tokens: { access: "jwt" } },
			messages,
		});

		const result = await oauthApi.callback({ code: "c", state: "s" });

		expect(result.tokens.access).toBe("jwt");
		expect(result.messages).toEqual(messages);
	});

	it("unlink sends the password as the request body", async () => {
		del.mockResolvedValue({ data: { user: { id: 1 } } });

		await oauthApi.unlink({ password: "pw" });

		expect(del).toHaveBeenCalledWith("/auth/google/unlink/", {
			password: "pw",
		});
	});
});

describe("unwrapOAuthResponse", () => {
	it("passes an already-flat response through", () => {
		const flat: OAuthInitiateResponse = {
			google_oauth_url: "u",
			state: "s",
			expires_in: 1,
		};
		expect(unwrapOAuthResponse<OAuthInitiateResponse>(flat)).toBe(flat);
	});
});
