import "@/i18n/config";
import { createTestQueryClient } from "@/lib/query/queryClient";
import { renderWithQueryClient } from "@/test-utils";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { circleKeys } from "../api/queryKeys";
import { circleServices } from "../api/services";
import type { CircleMembershipSummary } from "../types";
import { CircleOnThisDaySetting } from "./CircleOnThisDaySetting";

const membership = (
	circleId: number,
	on_this_day_frequency: string,
): CircleMembershipSummary => ({
	membership_id: circleId * 10,
	circle: {
		id: circleId,
		name: `Circle ${circleId}`,
		slug: `c${circleId}`,
		member_count: 2,
	},
	role: "member",
	is_owner: false,
	on_this_day_frequency,
	created_at: "2026-01-01T00:00:00Z",
});

function seededClient() {
	const queryClient = createTestQueryClient();
	queryClient.setQueryData<CircleMembershipSummary[]>(circleKeys.list(), [
		membership(7, "normal"),
		membership(8, "less"),
	]);
	return queryClient;
}

afterEach(() => {
	vi.restoreAllMocks();
});

describe("CircleOnThisDaySetting", () => {
	it("shows the viewer's frequency for this circle", () => {
		renderWithQueryClient(<CircleOnThisDaySetting circleId={8} />, {
			queryClient: seededClient(),
		});

		expect(screen.getByText("On this day")).toBeInTheDocument();
		expect(screen.getByRole("radio", { name: "Less" })).toBeChecked();
	});

	it("saves a new frequency for just this circle", async () => {
		const update = vi
			.spyOn(circleServices, "updateMyMembership")
			.mockResolvedValue({ data: { membership: membership(7, "more") } });
		const queryClient = seededClient();
		renderWithQueryClient(<CircleOnThisDaySetting circleId={7} />, {
			queryClient,
		});

		fireEvent.click(screen.getByRole("radio", { name: "More" }));

		await waitFor(() =>
			expect(screen.getByRole("radio", { name: "More" })).toBeChecked(),
		);
		await waitFor(() =>
			expect(update).toHaveBeenCalledWith(7, { on_this_day_frequency: "more" }),
		);
		const cached = queryClient.getQueryData<CircleMembershipSummary[]>(
			circleKeys.list(),
		);
		expect(cached?.map((item) => item.on_this_day_frequency)).toEqual([
			"more",
			"less",
		]);
	});

	it("goes back when the save fails", async () => {
		vi.spyOn(circleServices, "updateMyMembership").mockRejectedValue(
			new Error("nope"),
		);
		renderWithQueryClient(<CircleOnThisDaySetting circleId={7} />, {
			queryClient: seededClient(),
		});

		fireEvent.click(screen.getByRole("radio", { name: "Off" }));

		await waitFor(() =>
			expect(screen.getByRole("radio", { name: "Normal" })).toBeChecked(),
		);
	});
});
