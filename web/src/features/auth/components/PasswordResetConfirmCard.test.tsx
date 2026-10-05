import "@/i18n/config";
import { authKeys } from "@/features/auth/api/queryKeys";
import { authStore, setAccessToken } from "@/features/auth/store/authStore";
import { createTestQueryClient } from "@/lib/query/queryClient";
import { showToast } from "@/lib/toast";
import { renderWithQueryClient } from "@/test-utils";
import { getMockServer } from "@/test-utils/msw/server";
import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { afterEach, describe, expect, it, vi } from "vitest";

const navigate = vi.fn();

vi.mock("@tanstack/react-router", async (importOriginal) => ({
	...(await importOriginal<typeof import("@tanstack/react-router")>()),
	Link: ({ children, to }: { children?: React.ReactNode; to?: string }) => (
		<a href={to}>{children}</a>
	),
	useNavigate: () => navigate,
}));

vi.mock("@/lib/toast", async (importOriginal) => ({
	...(await importOriginal<typeof import("@/lib/toast")>()),
	showToast: vi.fn(),
}));

import { PasswordResetConfirmCard } from "./PasswordResetConfirmCard";

const CONFIRM_URL = "*/api/auth/password/reset/confirm/";
const NEW_PASSWORD = "Fresh-Lantern-42";

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

async function submit(password = NEW_PASSWORD) {
	await fill("New password", password);
	await fill("Confirm password", password);
	await act(async () => {
		fireEvent.click(screen.getByRole("button", { name: "Update password" }));
		await new Promise((resolve) => setTimeout(resolve, 50));
	});
}

function fieldOf(element: HTMLElement) {
	return element.closest(".form-group")?.querySelector("input");
}

afterEach(() => {
	vi.clearAllMocks();
	setAccessToken(null);
});

describe("PasswordResetConfirmCard", () => {
	it("shows server validation errors next to the right fields", async () => {
		(await server()).use(
			http.post(CONFIRM_URL, () =>
				HttpResponse.json(
					{
						error: "validation_failed",
						messages: [
							{
								i18n_key: "errors.password_too_common",
								context: { field: "password" },
							},
							{
								i18n_key: "errors.password_mismatch",
								context: { field: "password_confirm" },
							},
						],
					},
					{ status: 400 },
				),
			),
		);

		renderWithQueryClient(<PasswordResetConfirmCard token="reset-token" />);
		await submit("password1");

		const passwordError = await screen.findByText(
			"This password is too common. Choose something harder to guess.",
		);
		expect(fieldOf(passwordError)).toHaveAttribute("id", "password");
		const confirmError = screen.getByText("Passwords do not match");
		expect(fieldOf(confirmError)).toHaveAttribute("id", "password_confirm");
		// Field errors stand alone: no banner, no toast, no redirect.
		expect(screen.queryByRole("alert")).not.toBeInTheDocument();
		expect(showToast).not.toHaveBeenCalled();
		expect(navigate).not.toHaveBeenCalled();
	});

	it("shows the minimum length the server asks for", async () => {
		(await server()).use(
			http.post(CONFIRM_URL, () =>
				HttpResponse.json(
					{
						error: "validation_failed",
						messages: [
							{
								i18n_key: "errors.password_too_short",
								context: { field: "password", minLength: 12 },
							},
						],
					},
					{ status: 400 },
				),
			),
		);

		renderWithQueryClient(<PasswordResetConfirmCard token="reset-token" />);
		await submit();

		const error = await screen.findByText(
			"Password must be at least 12 characters",
		);
		expect(fieldOf(error)).toHaveAttribute("id", "password");
	});

	it("clears a server error once the field is edited", async () => {
		(await server()).use(
			http.post(CONFIRM_URL, () =>
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

		renderWithQueryClient(<PasswordResetConfirmCard token="reset-token" />);
		await submit("password1");
		const message =
			"This password is too common. Choose something harder to guess.";
		expect(await screen.findByText(message)).toBeInTheDocument();

		await fill("New password", NEW_PASSWORD);

		expect(screen.queryByText(message)).not.toBeInTheDocument();
	});

	it("shows an expired link as a general error", async () => {
		(await server()).use(
			http.post(CONFIRM_URL, () =>
				HttpResponse.json(
					{
						error: "invalid_token",
						messages: [{ i18n_key: "errors.token_invalid_expired" }],
					},
					{ status: 400 },
				),
			),
		);

		renderWithQueryClient(<PasswordResetConfirmCard token="old-token" />);
		await submit();

		expect(
			await screen.findByText("Invalid or expired token"),
		).toBeInTheDocument();
		expect(navigate).not.toHaveBeenCalled();
	});

	it("on success drops the local session and sends the user to log in", async () => {
		let body: unknown;
		(await server()).use(
			http.post(CONFIRM_URL, async ({ request }) => {
				body = await request.json();
				return HttpResponse.json({
					data: {},
					messages: [{ i18n_key: "notifications.auth.password_updated" }],
				});
			}),
		);
		// Signed-in users reach this page from "Set a password" in settings. The
		// reset revoked their refresh tokens, so the session can't be kept.
		setAccessToken("signed-in-access");
		const queryClient = createTestQueryClient();
		queryClient.setQueryData(authKeys.session(), { id: 1 });

		renderWithQueryClient(<PasswordResetConfirmCard token="reset-token" />, {
			queryClient,
		});
		await submit();

		expect(
			await screen.findByText("Password updated successfully"),
		).toBeInTheDocument();
		expect(body).toEqual({
			token: "reset-token",
			password: NEW_PASSWORD,
			password_confirm: NEW_PASSWORD,
		});
		expect(authStore.state.accessToken).toBeNull();
		expect(queryClient.getQueryData(authKeys.session())).toBeUndefined();
		await waitFor(
			() => expect(navigate).toHaveBeenCalledWith({ to: "/login" }),
			{
				timeout: 3000,
			},
		);
	});
});
