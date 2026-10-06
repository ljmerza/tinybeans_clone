import "@/i18n/config";
import { renderWithQueryClient } from "@/test-utils";
import { getMockServer } from "@/test-utils/msw/server";
import { act, fireEvent, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { afterEach, describe, expect, it, vi } from "vitest";

const navigate = vi.fn();

vi.mock("@tanstack/react-router", async (importOriginal) => ({
	...(await importOriginal<typeof import("@tanstack/react-router")>()),
	Link: ({
		children,
		to,
		...rest
	}: { children?: React.ReactNode; to?: string; "aria-label"?: string }) => (
		<a href={to} aria-label={rest["aria-label"]}>
			{children}
		</a>
	),
	useNavigate: () => navigate,
}));

vi.mock("../oauth/client", () => ({
	getOAuthProviders: () => Promise.resolve({ google: false, apple: false }),
	appleOauthApi: {},
}));

import { LoginCard } from "./LoginCard";

async function server() {
	const mockServer = await getMockServer();
	if (!mockServer) throw new Error("MSW is required for these tests");
	return mockServer;
}

// TanStack Form finishes validating after the event; let it settle inside act().
async function fill(label: string, value: string) {
	const input = screen.getByLabelText(label);
	await act(async () => {
		fireEvent.change(input, { target: { value } });
		fireEvent.blur(input);
	});
}

afterEach(() => {
	vi.clearAllMocks();
});

describe("LoginCard", () => {
	it("shows the welcome-back panel and every way out of the page", () => {
		renderWithQueryClient(<LoginCard />);

		expect(
			screen.getByRole("heading", { level: 1, name: "Login" }),
		).toBeInTheDocument();
		expect(
			screen.getByRole("heading", { level: 2, name: "Welcome back" }),
		).toBeInTheDocument();
		expect(
			screen.getByRole("link", { name: "Forgot password?" }),
		).toHaveAttribute("href", "/password/reset/request");
		expect(
			screen.getByRole("link", { name: "Login with Magic Link →" }),
		).toHaveAttribute("href", "/magic-link-request");
		expect(screen.getByRole("link", { name: "Sign up" })).toHaveAttribute(
			"href",
			"/signup",
		);
	});

	it("toggles password visibility", async () => {
		renderWithQueryClient(<LoginCard />);
		const password = screen.getByLabelText("Password");
		expect(password).toHaveAttribute("type", "password");
		expect(password).toHaveAttribute("autocomplete", "current-password");

		await act(async () => {
			fireEvent.click(screen.getByRole("button", { name: "Show password" }));
		});

		expect(password).toHaveAttribute("type", "text");
	});

	it("shows a failed sign-in as a form error", async () => {
		(await server()).use(
			http.post("*/api/auth/login/", () =>
				HttpResponse.json(
					{
						error: "invalid_credentials",
						messages: [{ i18n_key: "errors.invalid_credentials" }],
					},
					{ status: 400 },
				),
			),
		);

		renderWithQueryClient(<LoginCard />);
		await fill("Email", "ada@example.com");
		await fill("Password", "wrong-password");
		await act(async () => {
			fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
			await new Promise((resolve) => setTimeout(resolve, 50));
		});

		expect(
			await screen.findByText("Invalid email or password"),
		).toBeInTheDocument();
		expect(navigate).not.toHaveBeenCalled();
	});
});
