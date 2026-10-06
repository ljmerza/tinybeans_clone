import { renderWithQueryClient } from "@/test-utils";
import { screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const getOAuthProviders = vi.fn();

vi.mock("./client", () => ({
	getOAuthProviders: () => getOAuthProviders(),
	appleOauthApi: {},
}));
vi.mock("@tanstack/react-router", () => ({ useNavigate: () => vi.fn() }));
vi.mock("@/i18n", () => ({
	useApiMessages: () => ({ handleError: vi.fn(), showAsToast: vi.fn() }),
}));
vi.mock("react-i18next", async (importOriginal) => ({
	...(await importOriginal<typeof import("react-i18next")>()),
	useTranslation: () => ({ t: (key: string) => key }),
}));

import { AppleOAuthButton } from "./AppleOAuthButton";

describe("AppleOAuthButton", () => {
	beforeEach(() => {
		getOAuthProviders.mockReset();
	});

	it("stays hidden while Apple is not configured", async () => {
		getOAuthProviders.mockResolvedValue({ google: true, apple: false });
		renderWithQueryClient(<AppleOAuthButton mode="login" />);

		await waitFor(() => expect(getOAuthProviders).toHaveBeenCalled());
		expect(screen.queryByRole("button")).toBeNull();
	});

	it("stays hidden when the providers request fails", async () => {
		getOAuthProviders.mockRejectedValue(new Error("offline"));
		renderWithQueryClient(<AppleOAuthButton mode="login" />);

		await waitFor(() => expect(getOAuthProviders).toHaveBeenCalled());
		expect(screen.queryByRole("button")).toBeNull();
	});

	it("shows once the server reports Apple is configured", async () => {
		getOAuthProviders.mockResolvedValue({ google: true, apple: true });
		renderWithQueryClient(<AppleOAuthButton mode="signup" />);

		expect(
			await screen.findByRole("button", { name: "auth.oauth.apple_signup" }),
		).toBeTruthy();
	});
});
