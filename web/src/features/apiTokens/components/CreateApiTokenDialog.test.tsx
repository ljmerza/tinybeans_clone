import "@/i18n/config";
import * as reauthApi from "@/features/auth/reauth/api";
import { createHttpError } from "@/lib/httpClient";
import { createQueryPersistOptions } from "@/lib/query/persister";
import { createTestQueryClient } from "@/lib/query/queryClient";
import { renderWithQueryClient } from "@/test-utils";
import { persistQueryClientSave } from "@tanstack/react-query-persist-client";
import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { apiTokenServices } from "../api/services";
import { makeApiToken } from "../testData";
import { CreateApiTokenDialog, expiresAt } from "./CreateApiTokenDialog";

const PLAINTEXT = `circ_${"x".repeat(43)}`;
const DAY_MS = 86_400_000;

beforeEach(() => {
	// Radix Select scrolls the chosen option into view, which jsdom lacks.
	Element.prototype.scrollIntoView = vi.fn();
	vi.spyOn(reauthApi, "sendReauthCode").mockResolvedValue({});
	vi.spyOn(apiTokenServices, "list").mockResolvedValue({
		agent_api_enabled: true,
		tokens: [],
	});
	localStorage.clear();
});

afterEach(() => {
	vi.restoreAllMocks();
});

/** Mounts the dialog only while open, like the card does. */
function Harness({ onOpenChange }: { onOpenChange: (open: boolean) => void }) {
	const [open, setOpen] = useState(true);
	return open ? (
		<CreateApiTokenDialog
			circleId={7}
			onOpenChange={(next) => {
				onOpenChange(next);
				setOpen(next);
			}}
		/>
	) : null;
}

/** Fill in the details, continue, and type the emailed code. */
async function fillAndEnterCode(code = "123456") {
	fireEvent.change(screen.getByLabelText("Name"), {
		target: { value: "  Claude Code " },
	});
	fireEvent.click(screen.getByRole("button", { name: "Continue" }));
	await screen.findByText(/We sent a 6-digit code/);
	const submit = screen.getByRole("button", { name: "Create token" });
	expect(submit).toBeDisabled();
	// Five digits: not enough to submit.
	for (const [index, digit] of code.slice(0, 5).split("").entries()) {
		fireEvent.change(screen.getByLabelText(`Digit ${index + 1}`), {
			target: { value: digit },
		});
	}
	expect(submit).toBeDisabled();
	// The sixth submits by itself.
	await act(async () =>
		fireEvent.change(screen.getByLabelText("Digit 6"), {
			target: { value: code[5] },
		}),
	);
}

describe("CreateApiTokenDialog", () => {
	it("needs a name before asking for the code", () => {
		renderWithQueryClient(
			<CreateApiTokenDialog circleId={7} onOpenChange={vi.fn()} />,
		);

		expect(screen.getByRole("button", { name: "Continue" })).toBeDisabled();
		expect(reauthApi.sendReauthCode).not.toHaveBeenCalled();
	});

	it("creates a token with the emailed code and shows it once", async () => {
		const create = vi.spyOn(apiTokenServices, "create").mockResolvedValue({
			token: makeApiToken(),
			plaintext: PLAINTEXT,
		});
		const onOpenChange = vi.fn();
		const before = Date.now();
		const queryClient = createTestQueryClient();

		renderWithQueryClient(
			<CreateApiTokenDialog circleId={7} onOpenChange={onOpenChange} />,
			{ queryClient },
		);
		await fillAndEnterCode();

		expect(reauthApi.sendReauthCode).toHaveBeenCalledTimes(1);
		expect(create).toHaveBeenCalledTimes(1);
		const [circleId, input] = create.mock.calls[0];
		expect(circleId).toBe(7);
		expect(input).toMatchObject({
			name: "Claude Code",
			can_suggest: false,
			code: "123456",
		});
		// 90 days is the default expiry.
		const expiry = Date.parse(input.expires_at as string);
		expect(expiry).toBeGreaterThanOrEqual(before + 90 * DAY_MS);
		expect(expiry).toBeLessThanOrEqual(Date.now() + 90 * DAY_MS);

		expect(await screen.findByText(PLAINTEXT)).toBeInTheDocument();
		expect(
			screen.getByRole("heading", { name: "Your new API token" }),
		).toBeInTheDocument();
		// Never in localStorage: save the cache the way the app persists it
		// while the token is on screen, and look at what was written.
		const savedAfter = Date.now();
		await persistQueryClientSave({
			queryClient,
			...createQueryPersistOptions(),
		});
		const persisted = () => localStorage.getItem("circles-query-cache");
		await waitFor(
			() =>
				expect(
					JSON.parse(persisted() ?? "{}").timestamp,
				).toBeGreaterThanOrEqual(savedAfter),
			{ timeout: 3000 },
		);
		expect(persisted()).not.toContain("circ_");
	});

	it("can't be dismissed except by \"I've copied it\", which drops the plaintext", async () => {
		vi.spyOn(apiTokenServices, "create").mockResolvedValue({
			token: makeApiToken(),
			plaintext: PLAINTEXT,
		});
		const onOpenChange = vi.fn();
		const queryClient = createTestQueryClient();

		renderWithQueryClient(<Harness onOpenChange={onOpenChange} />, {
			queryClient,
		});
		await fillAndEnterCode();
		const dialog = await screen.findByRole("dialog", {
			name: "Your new API token",
		});

		expect(screen.queryByRole("button", { name: "Close" })).toBeNull();
		fireEvent.keyDown(dialog, { key: "Escape" });
		fireEvent.pointerDown(document.body);
		fireEvent.mouseDown(document.body);
		expect(screen.getByText(PLAINTEXT)).toBeInTheDocument();
		expect(onOpenChange).not.toHaveBeenCalled();
		const cachedMutations = () =>
			JSON.stringify(
				queryClient
					.getMutationCache()
					.getAll()
					.map((mutation) => mutation.state),
			);
		// Held only by the open dialog's mutation until then.
		expect(cachedMutations()).toContain(PLAINTEXT);

		fireEvent.click(screen.getByRole("button", { name: "I've copied it" }));

		expect(onOpenChange).toHaveBeenCalledWith(false);
		expect(screen.queryByText(PLAINTEXT)).toBeNull();
		await waitFor(() => expect(cachedMutations()).not.toContain("circ_"));
		expect(JSON.stringify({ ...localStorage })).not.toContain("circ_");
	});

	it("keeps asking for the code when it is wrong", async () => {
		vi.spyOn(apiTokenServices, "create").mockRejectedValue(
			createHttpError("Invalid", 400, {}, [
				{
					i18n_key: "errors.reauth_invalid_code",
					context: { field: "code" },
				},
			]),
		);

		renderWithQueryClient(
			<CreateApiTokenDialog circleId={7} onOpenChange={vi.fn()} />,
		);
		await fillAndEnterCode();

		expect(
			await screen.findByText(
				"That code is wrong or has expired. Check the newest email, or send a new code.",
			),
		).toBeInTheDocument();
		expect(screen.getByLabelText("Digit 1")).toHaveValue("");
		expect(screen.queryByText(/circ_/)).toBeNull();
	});

	it("shows the circle's token limit", async () => {
		vi.spyOn(apiTokenServices, "create").mockRejectedValue(
			createHttpError("Limit", 400, {}, [
				{ i18n_key: "errors.api_token_limit", context: { max: 10 } },
			]),
		);

		renderWithQueryClient(
			<CreateApiTokenDialog circleId={7} onOpenChange={vi.fn()} />,
		);
		await fillAndEnterCode();

		expect(
			await screen.findByText(
				"This circle already has the most API tokens allowed (10). Revoke one first.",
			),
		).toBeInTheDocument();
	});

	it("says to try again later when rate limited", async () => {
		vi.spyOn(apiTokenServices, "create").mockRejectedValue(
			createHttpError("Too many", 429, {}, [
				{ i18n_key: "errors.rate_limit_later", context: {} },
			]),
		);

		renderWithQueryClient(
			<CreateApiTokenDialog circleId={7} onOpenChange={vi.fn()} />,
		);
		await fillAndEnterCode();

		expect(
			await screen.findByText("Too many requests. Please try again later."),
		).toBeInTheDocument();
		expect(screen.queryByText(/\{\{/)).toBeNull();
	});
});

describe("expiresAt", () => {
	const now = new Date("2026-10-18T12:00:00Z");

	it("counts days from now", () => {
		expect(expiresAt("30", "", now)).toBe("2026-11-17T12:00:00.000Z");
		expect(expiresAt("365", "", now)).toBe("2027-10-18T12:00:00.000Z");
	});

	it("is null for never", () => {
		expect(expiresAt("never", "", now)).toBeNull();
	});

	it("ends a chosen day on the viewer's calendar", () => {
		expect(expiresAt("custom", "2027-01-31", now)).toBe(
			new Date(2027, 0, 31, 23, 59, 59).toISOString(),
		);
	});
});
