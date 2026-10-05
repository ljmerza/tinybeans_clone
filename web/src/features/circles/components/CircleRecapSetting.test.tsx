import "@/i18n/config";
import { createTestQueryClient } from "@/lib/query/queryClient";
import { renderWithQueryClient } from "@/test-utils";
import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { circleKeys } from "../api/queryKeys";
import { circleServices } from "../api/services";
import type { CircleMembersPayload } from "../hooks/useCircleMemberships";
import { CircleRecapSetting } from "./CircleRecapSetting";

const circle = {
	id: 7,
	name: "Family",
	slug: "family",
	member_count: 2,
	monthly_recap_enabled: false,
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

describe("CircleRecapSetting", () => {
	it("shows whether recaps are on", () => {
		renderWithQueryClient(<CircleRecapSetting circleId={7} enabled />);

		expect(
			screen.getByRole("switch", { name: "Monthly recap album" }),
		).toBeChecked();
		expect(
			screen.getByText(/On the 1st of each month, make an album/),
		).toBeInTheDocument();
	});

	it("turns recaps on and updates the circle", async () => {
		const update = vi.spyOn(circleServices, "updateCircle").mockResolvedValue({
			data: { circle: { ...circle, monthly_recap_enabled: true } },
		});
		const queryClient = seededClient();

		renderWithQueryClient(<CircleRecapSetting circleId={7} enabled={false} />, {
			queryClient,
		});
		const toggle = screen.getByRole("switch", { name: "Monthly recap album" });
		expect(toggle).not.toBeChecked();
		await act(async () => fireEvent.click(toggle));

		expect(update).toHaveBeenCalledWith(7, { monthly_recap_enabled: true });
		await waitFor(() =>
			expect(
				queryClient.getQueryData<CircleMembersPayload>(circleKeys.members(7))
					?.circle.monthly_recap_enabled,
			).toBe(true),
		);
	});

	it("turns recaps off", async () => {
		const update = vi.spyOn(circleServices, "updateCircle").mockResolvedValue({
			data: { circle },
		});

		renderWithQueryClient(<CircleRecapSetting circleId={7} enabled />, {
			queryClient: seededClient(),
		});
		await act(async () =>
			fireEvent.click(
				screen.getByRole("switch", { name: "Monthly recap album" }),
			),
		);

		expect(update).toHaveBeenCalledWith(7, { monthly_recap_enabled: false });
	});

	it("falls back to the saved state when saving fails", async () => {
		vi.spyOn(circleServices, "updateCircle").mockRejectedValue(
			Object.assign(new Error("Forbidden"), { status: 403 }),
		);

		renderWithQueryClient(<CircleRecapSetting circleId={7} enabled={false} />);
		const toggle = screen.getByRole("switch", { name: "Monthly recap album" });
		await act(async () => fireEvent.click(toggle));

		await waitFor(() => expect(toggle).toBeEnabled());
		expect(toggle).not.toBeChecked();
	});
});
