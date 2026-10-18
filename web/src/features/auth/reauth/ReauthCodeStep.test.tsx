import "@/i18n/config";
import { createHttpError } from "@/lib/httpClient";
import { renderWithQueryClient } from "@/test-utils";
import { act, fireEvent, screen } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ReauthCodeStep } from "./ReauthCodeStep";
import * as api from "./api";

function Harness({ error }: { error?: string }) {
	const [code, setCode] = useState("");
	return (
		<>
			<ReauthCodeStep value={code} onChange={setCode} error={error} />
			<output data-testid="code">{code}</output>
		</>
	);
}

afterEach(() => {
	vi.restoreAllMocks();
});

describe("ReauthCodeStep", () => {
	it("emails a code once when it opens", async () => {
		const send = vi.spyOn(api, "sendReauthCode").mockResolvedValue({});

		renderWithQueryClient(<Harness />);

		expect(
			await screen.findByText(
				"We sent a 6-digit code to your email. It expires in 10 minutes.",
			),
		).toBeInTheDocument();
		expect(send).toHaveBeenCalledTimes(1);
		expect(screen.getAllByRole("textbox")).toHaveLength(6);
	});

	it("resends a code and clears what was typed", async () => {
		const send = vi.spyOn(api, "sendReauthCode").mockResolvedValue({});

		renderWithQueryClient(<Harness />);
		await screen.findByText(/We sent a 6-digit code/);
		fireEvent.change(screen.getByLabelText("Digit 1"), {
			target: { value: "4" },
		});
		expect(screen.getByTestId("code")).toHaveTextContent("4");
		await act(async () =>
			fireEvent.click(screen.getByRole("button", { name: "Resend code" })),
		);

		expect(send).toHaveBeenCalledTimes(2);
		expect(
			await screen.findByText(
				"We sent a new code to your email. Use the newest one.",
			),
		).toBeInTheDocument();
		expect(screen.getByTestId("code")).toBeEmptyDOMElement();
	});

	it("explains a refused send with the API's message", async () => {
		vi.spyOn(api, "sendReauthCode").mockRejectedValue(
			createHttpError("Too many", 429, {}, [
				{ i18n_key: "errors.reauth_rate_limited" },
			]),
		);

		renderWithQueryClient(<Harness />);

		expect(
			await screen.findByText(
				"Too many codes requested. Please wait a few minutes and try again.",
			),
		).toBeInTheDocument();
	});

	it("shows why a code was refused", async () => {
		vi.spyOn(api, "sendReauthCode").mockResolvedValue({});

		renderWithQueryClient(<Harness error="That code is wrong." />);

		expect(await screen.findByText("That code is wrong.")).toBeInTheDocument();
	});
});
