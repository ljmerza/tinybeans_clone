import "@/i18n/config";
import { renderWithQueryClient } from "@/test-utils";
import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { apiTokenServices } from "../api/services";
import { makeApiToken } from "../testData";
import type { ApiToken } from "../types";
import { CircleApiTokensCard } from "./CircleApiTokensCard";

function mockList(tokens: ApiToken[], agentApiEnabled = true) {
	return vi
		.spyOn(apiTokenServices, "list")
		.mockResolvedValue({ agent_api_enabled: agentApiEnabled, tokens });
}

afterEach(() => {
	vi.restoreAllMocks();
});

describe("CircleApiTokensCard", () => {
	it("lists the circle's tokens without their secrets", async () => {
		const list = mockList([
			makeApiToken({
				can_suggest: true,
				last_used_at: "2026-10-17T09:30:00Z",
				last_used_ip: "192.168.1.20",
			}),
			makeApiToken({
				id: "11111111-0000-0000-0000-000000000002",
				name: "Old laptop",
				display_prefix: "circ_old0000",
				status: "revoked",
				revoked_at: new Date().toISOString(),
				revoked_reason: "creator_not_admin",
				expires_at: "2027-01-01T00:00:00Z",
			}),
		]);

		renderWithQueryClient(<CircleApiTokensCard circleId={7} />);

		expect(await screen.findByText("Claude Code")).toBeInTheDocument();
		expect(list).toHaveBeenCalledWith(7);
		expect(screen.getByText("circ_abc1234…")).toBeInTheDocument();
		expect(screen.getByText("Can suggest")).toBeInTheDocument();
		expect(screen.getByText("Never expires")).toBeInTheDocument();
		expect(screen.getByText(/from 192\.168\.1\.20/)).toBeInTheDocument();
		expect(
			screen.getByText("Revoked: its creator is no longer a circle admin"),
		).toBeInTheDocument();
		expect(screen.getByText("Never used")).toBeInTheDocument();
		// Only active tokens can be revoked.
		expect(
			screen.getByRole("button", { name: "Revoke Claude Code" }),
		).toBeInTheDocument();
		expect(
			screen.queryByRole("button", { name: "Revoke Old laptop" }),
		).toBeNull();
	});

	it("says when the server operator has turned the API off", async () => {
		mockList([makeApiToken()], false);

		renderWithQueryClient(<CircleApiTokensCard circleId={7} />);

		expect(
			await screen.findByText("Disabled by the server operator"),
		).toBeInTheDocument();
		expect(screen.getByRole("button", { name: "Create token" })).toBeDisabled();
	});

	it("revokes a token only after confirming", async () => {
		mockList([makeApiToken()]);
		const revoke = vi
			.spyOn(apiTokenServices, "revoke")
			.mockResolvedValue(undefined);

		renderWithQueryClient(<CircleApiTokensCard circleId={7} />);
		fireEvent.click(
			await screen.findByRole("button", { name: "Revoke Claude Code" }),
		);

		expect(
			await screen.findByRole("alertdialog", { name: "Revoke this token?" }),
		).toBeInTheDocument();
		expect(
			screen.getByText(
				'"Claude Code" stops working at once. This can\'t be undone.',
			),
		).toBeInTheDocument();
		expect(revoke).not.toHaveBeenCalled();
		await act(async () =>
			fireEvent.click(screen.getByRole("button", { name: "Revoke token" })),
		);

		expect(revoke).toHaveBeenCalledWith(7, makeApiToken().id);
		await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
	});

	it("collapses tokens that stopped working over 30 days ago", async () => {
		mockList([
			makeApiToken(),
			makeApiToken({
				id: "11111111-0000-0000-0000-000000000003",
				name: "Ancient",
				status: "expired",
				expires_at: "2025-01-01T00:00:00Z",
			}),
		]);

		renderWithQueryClient(<CircleApiTokensCard circleId={7} />);
		await screen.findByText("Claude Code");

		expect(screen.queryByText("Ancient")).toBeNull();
		fireEvent.click(screen.getByRole("button", { name: "Show 1 older token" }));
		expect(screen.getByText("Ancient")).toBeInTheDocument();
		expect(screen.getByText("Expired")).toBeInTheDocument();
	});

	it("says when there are no tokens", async () => {
		mockList([]);

		renderWithQueryClient(<CircleApiTokensCard circleId={7} />);

		expect(await screen.findByText("No tokens yet.")).toBeInTheDocument();
	});
});
