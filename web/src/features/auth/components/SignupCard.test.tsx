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

import { SignupCard } from "./SignupCard";

const SIGNUP_URL = "*/api/auth/signup/";

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

function fieldOf(element: HTMLElement) {
	return element.closest(".form-group")?.querySelector("input");
}

afterEach(() => {
	vi.clearAllMocks();
});

describe("SignupCard", () => {
	it("shows the brand link home and the brand panel", () => {
		renderWithQueryClient(<SignupCard />);

		expect(
			screen.getByRole("heading", { level: 1, name: "Create your account" }),
		).toBeInTheDocument();
		for (const link of screen.getAllByRole("link", { name: "Circles home" })) {
			expect(link).toHaveAttribute("href", "/");
		}
		// Once in the large-screen panel, once in the small-screen list.
		expect(
			screen.getAllByText("Only people you invite can see your posts"),
		).toHaveLength(2);
	});

	it("toggles password visibility", async () => {
		renderWithQueryClient(<SignupCard />);
		const password = screen.getByLabelText("Password");
		expect(password).toHaveAttribute("type", "password");

		const [toggle] = screen.getAllByRole("button", { name: "Show password" });
		await act(async () => {
			fireEvent.click(toggle);
		});

		expect(password).toHaveAttribute("type", "text");
		expect(toggle).toHaveAccessibleName("Hide password");
		expect(toggle).toHaveAttribute("aria-pressed", "true");
		// The confirm field keeps its own toggle.
		expect(screen.getByLabelText("Confirm password")).toHaveAttribute(
			"type",
			"password",
		);
	});

	it("rates the password once typing starts", async () => {
		renderWithQueryClient(<SignupCard />);
		expect(screen.queryByTestId("password-strength")).not.toBeInTheDocument();

		await fill("Password", "short");
		expect(screen.getByTestId("password-strength")).toHaveTextContent(
			"Password strength: Too short",
		);

		await fill("Password", "Fresh-Lantern-42");
		expect(screen.getByTestId("password-strength")).toHaveTextContent(
			"Password strength: Strong",
		);
	});

	it("shows a server password error under the password field", async () => {
		(await server()).use(
			http.post(SIGNUP_URL, () =>
				HttpResponse.json(
					{
						error: "validation_failed",
						messages: [
							{
								i18n_key: "errors.password_too_common",
								context: { field: "password" },
							},
						],
					},
					{ status: 400 },
				),
			),
		);

		renderWithQueryClient(<SignupCard />);
		await fill("First name", "Ada");
		await fill("Last name", "Lovelace");
		await fill("Email", "ada@example.com");
		await fill("Password", "password1");
		await fill("Confirm password", "password1");
		await act(async () => {
			fireEvent.click(screen.getByRole("button", { name: "Create account" }));
			await new Promise((resolve) => setTimeout(resolve, 50));
		});

		const error = await screen.findByText(
			"This password is too common. Choose something harder to guess.",
		);
		expect(fieldOf(error)).toHaveAttribute("id", "password");
		expect(navigate).not.toHaveBeenCalled();
	});

	it("shows an invited email instead of an email field", () => {
		renderWithQueryClient(<SignupCard prefillEmail="invitee@example.com" />);

		expect(screen.queryByLabelText("Email")).not.toBeInTheDocument();
		expect(screen.getByTestId("prefilled-email")).toHaveValue(
			"invitee@example.com",
		);
	});
});
