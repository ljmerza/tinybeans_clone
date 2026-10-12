import "@/i18n/config";
import { createTestQueryClient } from "@/lib/query/queryClient";
import { renderWithQueryClient } from "@/test-utils";
import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { circleKeys } from "../api/queryKeys";
import { circleServices } from "../api/services";
import type { CircleMembersPayload } from "../hooks/useCircleMemberships";
import { CircleOnThisDaySetting } from "./CircleOnThisDaySetting";

const circle = {
	id: 7,
	name: "Family",
	slug: "family",
	member_count: 2,
	on_this_day_frequency: "normal",
};

function seededClient() {
	const queryClient = createTestQueryClient();
	queryClient.setQueryData<CircleMembersPayload>(circleKeys.members(7), {
		circle,
		members: [],
	});
	return queryClient;
}

afterEach(() => {
	vi.restoreAllMocks();
});

describe("CircleOnThisDaySetting", () => {
	it("shows the circle's frequency", () => {
		renderWithQueryClient(
			<CircleOnThisDaySetting circleId={7} frequency="less" />,
		);

		expect(screen.getByText("On this day")).toBeInTheDocument();
		expect(screen.getByRole("radio", { name: "Less" })).toBeChecked();
	});

	it("treats a missing setting as normal", () => {
		renderWithQueryClient(<CircleOnThisDaySetting circleId={7} />);

		expect(screen.getByRole("radio", { name: "Normal" })).toBeChecked();
	});

	it("saves a new frequency and updates the circle", async () => {
		const update = vi.spyOn(circleServices, "updateCircle").mockResolvedValue({
			data: { circle: { ...circle, on_this_day_frequency: "more" } },
		});
		const queryClient = seededClient();
		renderWithQueryClient(
			<CircleOnThisDaySetting circleId={7} frequency="normal" />,
			{ queryClient },
		);

		await act(async () =>
			fireEvent.click(screen.getByRole("radio", { name: "More" })),
		);

		expect(update).toHaveBeenCalledWith(7, { on_this_day_frequency: "more" });
		await waitFor(() =>
			expect(
				queryClient.getQueryData<CircleMembersPayload>(circleKeys.members(7))
					?.circle.on_this_day_frequency,
			).toBe("more"),
		);
	});

	it("goes back when the save fails", async () => {
		vi.spyOn(circleServices, "updateCircle").mockRejectedValue(
			new Error("nope"),
		);
		renderWithQueryClient(
			<CircleOnThisDaySetting circleId={7} frequency="normal" />,
			{ queryClient: seededClient() },
		);

		fireEvent.click(screen.getByRole("radio", { name: "Off" }));

		await waitFor(() =>
			expect(screen.getByRole("radio", { name: "Normal" })).toBeChecked(),
		);
	});
});
