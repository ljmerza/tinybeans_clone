import "@/i18n/config";
import { createHttpError } from "@/lib/httpClient";
import { renderWithQueryClient } from "@/test-utils";
import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import { toast } from "sonner";
import { afterEach, describe, expect, it, vi } from "vitest";

import { aiAssistServices } from "../api/services";
import type { AvailableAiSettings } from "../types";
import { CircleAiSetting } from "./CircleAiSetting";

const settings = (
	overrides: Partial<AvailableAiSettings> = {},
): AvailableAiSettings => ({
	available: true,
	enabled: false,
	acknowledged_at: null,
	last_run_at: null,
	last_success_at: null,
	last_error: "",
	pending_count: 0,
	...overrides,
});

afterEach(() => {
	vi.restoreAllMocks();
});

describe("CircleAiSetting", () => {
	it("renders nothing while the operator hasn't set AI up", async () => {
		const get = vi
			.spyOn(aiAssistServices, "getSettings")
			.mockResolvedValue({ available: false });

		const { container } = renderWithQueryClient(
			<CircleAiSetting circleId={7} />,
		);

		await waitFor(() => expect(get).toHaveBeenCalledWith(7));
		expect(container).toBeEmptyDOMElement();
	});

	it("turns on only once the data-sharing notice is accepted", async () => {
		vi.spyOn(aiAssistServices, "getSettings").mockResolvedValue(settings());
		const update = vi
			.spyOn(aiAssistServices, "updateSettings")
			.mockResolvedValue(settings({ enabled: true }));

		renderWithQueryClient(<CircleAiSetting circleId={7} />);
		const toggle = await screen.findByRole("switch", {
			name: "AI milestone suggestions",
		});
		expect(toggle).not.toBeChecked();
		fireEvent.click(toggle);

		expect(
			await screen.findByText(
				"Captions from this circle will be sent to the AI service this site's operator has set up, to suggest milestones. Comments, names and photos are not sent.",
			),
		).toBeInTheDocument();
		const confirm = screen.getByRole("button", { name: "Turn on" });
		expect(confirm).toBeDisabled();
		fireEvent.click(confirm);
		expect(update).not.toHaveBeenCalled();

		fireEvent.click(
			screen.getByRole("checkbox", {
				name: "I understand that this circle's captions will be sent to that AI service.",
			}),
		);
		expect(confirm).toBeEnabled();
		await act(async () => fireEvent.click(confirm));

		expect(update).toHaveBeenCalledWith(7, {
			enabled: true,
			acknowledge_data_sharing: true,
		});
		await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
		expect(
			screen.getByRole("switch", { name: "AI milestone suggestions" }),
		).toBeChecked();
	});

	it("cancelling the notice leaves it off", async () => {
		vi.spyOn(aiAssistServices, "getSettings").mockResolvedValue(settings());
		const update = vi.spyOn(aiAssistServices, "updateSettings");

		renderWithQueryClient(<CircleAiSetting circleId={7} />);
		fireEvent.click(
			await screen.findByRole("switch", { name: "AI milestone suggestions" }),
		);
		fireEvent.click(await screen.findByRole("button", { name: "Cancel" }));

		await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
		expect(update).not.toHaveBeenCalled();
		expect(
			screen.getByRole("switch", { name: "AI milestone suggestions" }),
		).not.toBeChecked();
	});

	it("turns off without asking", async () => {
		vi.spyOn(aiAssistServices, "getSettings").mockResolvedValue(
			settings({ enabled: true }),
		);
		const update = vi
			.spyOn(aiAssistServices, "updateSettings")
			.mockResolvedValue(settings());

		renderWithQueryClient(<CircleAiSetting circleId={7} />);
		await act(async () =>
			fireEvent.click(
				await screen.findByRole("switch", {
					name: "AI milestone suggestions",
				}),
			),
		);

		expect(update).toHaveBeenCalledWith(7, { enabled: false });
		expect(screen.queryByRole("alertdialog")).toBeNull();
	});

	it("shows the scan status and translates error codes", async () => {
		vi.spyOn(aiAssistServices, "getSettings").mockResolvedValue(
			settings({
				enabled: true,
				last_success_at: "2026-10-17T05:00:00Z",
				last_error: "unreachable",
				pending_count: 3,
			}),
		);

		renderWithQueryClient(<CircleAiSetting circleId={7} />);

		expect(
			await screen.findByText(/^Last successful scan: /),
		).toBeInTheDocument();
		expect(
			screen.getByText(
				"The last scan stopped: The AI service couldn't be reached.",
			),
		).toBeInTheDocument();
		expect(
			screen.getByText("3 suggestions waiting for review"),
		).toBeInTheDocument();
	});

	it("tests the connection and shows the outcome", async () => {
		vi.spyOn(aiAssistServices, "getSettings").mockResolvedValue(settings());
		const test = vi
			.spyOn(aiAssistServices, "testConnection")
			.mockResolvedValueOnce({
				ok: false,
				code: "model_missing",
				latency_ms: 40,
			})
			.mockResolvedValueOnce({ ok: true, code: "ok", latency_ms: 812 });

		renderWithQueryClient(<CircleAiSetting circleId={7} />);
		const button = await screen.findByRole("button", {
			name: "Test connection",
		});
		await act(async () => fireEvent.click(button));

		expect(
			await screen.findByText(
				"The connection failed: The AI model isn't available.",
			),
		).toBeInTheDocument();
		await act(async () => fireEvent.click(button));
		expect(
			await screen.findByText("The connection works (812 ms)."),
		).toBeInTheDocument();
		expect(test).toHaveBeenCalledTimes(2);
	});

	it("scans now only while it is on, and explains a refusal", async () => {
		vi.spyOn(aiAssistServices, "getSettings").mockResolvedValue(
			settings({ enabled: true }),
		);
		const scan = vi
			.spyOn(aiAssistServices, "scanNow")
			.mockRejectedValue(
				createHttpError("Running", 409, {}, [{ i18n_key: "ai.scan_running" }]),
			);
		const errorToast = vi.spyOn(toast, "error");

		renderWithQueryClient(<CircleAiSetting circleId={7} />);
		await act(async () =>
			fireEvent.click(await screen.findByRole("button", { name: "Scan now" })),
		);

		expect(scan).toHaveBeenCalledWith(7);
		await waitFor(() =>
			expect(errorToast).toHaveBeenCalledWith(
				"A scan is already running. Please try again later.",
				expect.anything(),
			),
		);
	});

	it("has no Scan now button while it is off", async () => {
		vi.spyOn(aiAssistServices, "getSettings").mockResolvedValue(settings());

		renderWithQueryClient(<CircleAiSetting circleId={7} />);

		await screen.findByRole("button", { name: "Test connection" });
		expect(screen.queryByRole("button", { name: "Scan now" })).toBeNull();
	});
});
