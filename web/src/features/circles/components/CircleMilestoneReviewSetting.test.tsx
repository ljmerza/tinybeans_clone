import "@/i18n/config";
import { createTestQueryClient } from "@/lib/query/queryClient";
import { renderWithQueryClient } from "@/test-utils";
import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { circleKeys } from "../api/queryKeys";
import { circleServices } from "../api/services";
import type { CircleMembersPayload } from "../hooks/useCircleMemberships";
import { CircleMilestoneReviewSetting } from "./CircleMilestoneReviewSetting";

const circle = {
	id: 7,
	name: "Family",
	slug: "family",
	member_count: 2,
	review_ai_milestones: false,
};

afterEach(() => {
	vi.restoreAllMocks();
});

describe("CircleMilestoneReviewSetting", () => {
	it("is off by default", () => {
		renderWithQueryClient(
			<CircleMilestoneReviewSetting circleId={7} enabled={false} />,
		);

		expect(
			screen.getByRole("switch", { name: "Review AI milestone picks" }),
		).not.toBeChecked();
	});

	it("turns review on and updates the circle", async () => {
		const update = vi.spyOn(circleServices, "updateCircle").mockResolvedValue({
			data: { circle: { ...circle, review_ai_milestones: true } },
		});
		const queryClient = createTestQueryClient();
		queryClient.setQueryData<CircleMembersPayload>(circleKeys.members(7), {
			circle,
			members: [],
		});

		renderWithQueryClient(
			<CircleMilestoneReviewSetting circleId={7} enabled={false} />,
			{ queryClient },
		);
		await act(async () =>
			fireEvent.click(
				screen.getByRole("switch", { name: "Review AI milestone picks" }),
			),
		);

		expect(update).toHaveBeenCalledWith(7, { review_ai_milestones: true });
		await waitFor(() =>
			expect(
				queryClient.getQueryData<CircleMembersPayload>(circleKeys.members(7))
					?.circle.review_ai_milestones,
			).toBe(true),
		);
	});
});
