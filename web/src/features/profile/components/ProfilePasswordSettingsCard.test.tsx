import "@/i18n/config";
import { authStore, setAccessToken } from "@/features/auth/store/authStore";
import { showToast } from "@/lib/toast";
import { renderWithQueryClient } from "@/test-utils";
import { getMockServer } from "@/test-utils/msw/server";
import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ProfilePasswordSettingsCard } from "./ProfilePasswordSettingsCard";

vi.mock("@/lib/toast", async (importOriginal) => ({
	...(await importOriginal<typeof import("@/lib/toast")>()),
	showToast: vi.fn(),
}));

const CHANGE_URL = "*/api/auth/password/change/";
const NEW_PASSWORD = "Fresh-Lantern-42";

async function server() {
	const mockServer = await getMockServer();
	if (!mockServer) throw new Error("MSW is required for these tests");
	return mockServer;
}

async function mockProfile(hasUsablePassword: boolean) {
	(await server()).use(
		http.get("*/api/users/me/", () =>
			HttpResponse.json({
				data: {
					user: {
						id: 1,
						email: "member@example.com",
						has_usable_password: hasUsablePassword,
					},
				},
			}),
		),
	);
}

// TanStack Form finishes validating after the event; let it settle inside act().
async function fill(label: string, value: string) {
	const input = screen.getByLabelText(label);
	await act(async () => {
		fireEvent.change(input, { target: { value } });
		fireEvent.blur(input);
	});
}

async function fillForm(confirm = NEW_PASSWORD) {
	await screen.findByLabelText("Current password");
	await fill("Current password", "password123");
	await fill("New password", NEW_PASSWORD);
	await fill("Confirm new password", confirm);
}

// The submit is async (validation, then the request); wait for it inside act().
async function submit() {
	await act(async () => {
		fireEvent.click(screen.getByRole("button", { name: "Change password" }));
		await new Promise((resolve) => setTimeout(resolve, 50));
	});
}

beforeEach(() => {
	setAccessToken("old-access");
});

afterEach(() => {
	vi.clearAllMocks();
	setAccessToken(null);
});

describe("ProfilePasswordSettingsCard", () => {
	it("renders the change password form", async () => {
		await mockProfile(true);

		renderWithQueryClient(<ProfilePasswordSettingsCard />);

		expect(
			await screen.findByRole("heading", { name: "Password" }),
		).toBeInTheDocument();
		expect(screen.getByLabelText("Current password")).toHaveAttribute(
			"autocomplete",
			"current-password",
		);
		expect(screen.getByLabelText("New password")).toHaveAttribute(
			"type",
			"password",
		);
		expect(screen.getByLabelText("Confirm new password")).toBeInTheDocument();
		expect(
			screen.getByRole("button", { name: "Change password" }),
		).toBeInTheDocument();
	});

	it("blocks submit when the confirmation does not match", async () => {
		await mockProfile(true);
		const calls = vi.fn();
		(await server()).use(
			http.post(CHANGE_URL, () => {
				calls();
				return HttpResponse.json({ data: {} });
			}),
		);

		renderWithQueryClient(<ProfilePasswordSettingsCard />);
		await fillForm("Something-Else-77");
		await submit();

		expect(
			await screen.findByText("Passwords do not match"),
		).toBeInTheDocument();
		expect(calls).not.toHaveBeenCalled();
	});

	it("blocks a new password shorter than 8 characters", async () => {
		await mockProfile(true);

		renderWithQueryClient(<ProfilePasswordSettingsCard />);
		await screen.findByLabelText("New password");
		await fill("New password", "short");

		expect(
			await screen.findByText("Password must be at least 8 characters"),
		).toBeInTheDocument();
	});

	it("shows server validation errors next to the right fields", async () => {
		await mockProfile(true);
		(await server()).use(
			http.post(CHANGE_URL, () =>
				HttpResponse.json(
					{
						error: "validation_failed",
						messages: [
							{
								i18n_key: "errors.auth.invalid_password",
								context: { field: "current_password" },
							},
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

		renderWithQueryClient(<ProfilePasswordSettingsCard />);
		await fillForm();
		await submit();

		const currentError = await screen.findByText("Invalid password");
		expect(
			currentError.closest(".form-group")?.querySelector("input"),
		).toHaveAttribute("id", "current_password");
		const passwordError = screen.getByText(
			"This password is too common. Choose something harder to guess.",
		);
		expect(
			passwordError.closest(".form-group")?.querySelector("input"),
		).toHaveAttribute("id", "password");
		// Field errors stand alone; no generic failure banner on top of them.
		expect(screen.queryByRole("alert")).not.toBeInTheDocument();
		expect(showToast).not.toHaveBeenCalled();
		expect(authStore.state.accessToken).toBe("old-access");
	});

	it("explains a rate-limited response", async () => {
		await mockProfile(true);
		(await server()).use(
			http.post(CHANGE_URL, () =>
				HttpResponse.json(
					{
						error: "rate_limit_exceeded",
						messages: [{ i18n_key: "errors.password_change_rate_limit" }],
					},
					{ status: 429 },
				),
			),
		);

		renderWithQueryClient(<ProfilePasswordSettingsCard />);
		await fillForm();
		await submit();

		expect(
			await screen.findByText(
				"Too many password change attempts. Please wait a few minutes and try again.",
			),
		).toBeInTheDocument();
	});

	it("on success adopts the new access token, clears the form and toasts", async () => {
		await mockProfile(true);
		let body: unknown;
		(await server()).use(
			http.post(CHANGE_URL, async ({ request }) => {
				body = await request.json();
				return HttpResponse.json({
					data: { tokens: { access: "new-access" } },
					messages: [{ i18n_key: "notifications.auth.password_updated" }],
				});
			}),
		);

		renderWithQueryClient(<ProfilePasswordSettingsCard />);
		await fillForm();
		await submit();

		await waitFor(() =>
			expect(showToast).toHaveBeenCalledWith({
				message: "Password changed. Your other devices have been signed out.",
				level: "success",
			}),
		);
		expect(body).toEqual({
			current_password: "password123",
			password: NEW_PASSWORD,
			password_confirm: NEW_PASSWORD,
		});
		expect(authStore.state.accessToken).toBe("new-access");
		await waitFor(() =>
			expect(screen.getByLabelText("Current password")).toHaveValue(""),
		);
		expect(screen.getByLabelText("New password")).toHaveValue("");
		expect(screen.getByLabelText("Confirm new password")).toHaveValue("");
	});

	it("offers an emailed set-password link when the account has no password", async () => {
		await mockProfile(false);
		let body: unknown;
		(await server()).use(
			http.post("*/api/auth/password/reset/request/", async ({ request }) => {
				body = await request.json();
				return HttpResponse.json(
					{
						data: {},
						messages: [{ i18n_key: "notifications.auth.password_reset" }],
					},
					{ status: 202 },
				);
			}),
		);

		renderWithQueryClient(<ProfilePasswordSettingsCard />);

		expect(
			await screen.findByRole("heading", { name: "Set a password" }),
		).toBeInTheDocument();
		expect(screen.queryByLabelText("Current password")).not.toBeInTheDocument();

		fireEvent.click(screen.getByRole("button", { name: "Email me a link" }));

		expect(
			await screen.findByText(
				"Check member@example.com for a link to set your password.",
			),
		).toBeInTheDocument();
		expect(body).toEqual({ email: "member@example.com" });
	});
});
