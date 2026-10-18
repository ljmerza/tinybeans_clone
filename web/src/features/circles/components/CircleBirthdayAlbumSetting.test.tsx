import "@/i18n/config";
import { createTestQueryClient } from "@/lib/query/queryClient";
import { renderWithQueryClient } from "@/test-utils";
import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { circleKeys } from "../api/queryKeys";
import { circleServices } from "../api/services";
import type { CircleMembersPayload } from "../hooks/useCircleMemberships";
import type { CircleChild } from "../types";
import { CircleBirthdayAlbumSetting } from "./CircleBirthdayAlbumSetting";

const circle = {
	id: 7,
	name: "Family",
	slug: "family",
	member_count: 2,
	birthday_album_enabled: false,
};

const sophia: CircleChild = {
	id: "c1",
	display_name: "Sophia",
	birthdate: "2023-10-16",
};
const aubrey: CircleChild = {
	id: "c2",
	display_name: "Aubrey",
	birthdate: null,
};

function seededClient() {
	const queryClient = createTestQueryClient();
	queryClient.setQueryData<CircleMembersPayload>(circleKeys.members(7), {
		circle,
		members: [],
	});
	return queryClient;
}

function mockChildren(children: CircleChild[]) {
	return vi
		.spyOn(circleServices, "listChildren")
		.mockResolvedValue({ data: { children } });
}

afterEach(() => {
	vi.restoreAllMocks();
});

describe("CircleBirthdayAlbumSetting", () => {
	it("is off without listing children", () => {
		const list = mockChildren([sophia]);

		renderWithQueryClient(
			<CircleBirthdayAlbumSetting circleId={7} enabled={false} />,
		);

		expect(
			screen.getByRole("switch", { name: "Birthdays album" }),
		).not.toBeChecked();
		expect(screen.queryByText("Children's birthdates")).toBeNull();
		expect(list).not.toHaveBeenCalled();
	});

	it("turns it on and updates the circle", async () => {
		mockChildren([]);
		const update = vi.spyOn(circleServices, "updateCircle").mockResolvedValue({
			data: { circle: { ...circle, birthday_album_enabled: true } },
		});
		const queryClient = seededClient();

		renderWithQueryClient(
			<CircleBirthdayAlbumSetting circleId={7} enabled={false} />,
			{ queryClient },
		);
		await act(async () =>
			fireEvent.click(screen.getByRole("switch", { name: "Birthdays album" })),
		);

		expect(update).toHaveBeenCalledWith(7, { birthday_album_enabled: true });
		await waitFor(() =>
			expect(
				queryClient.getQueryData<CircleMembersPayload>(circleKeys.members(7))
					?.circle.birthday_album_enabled,
			).toBe(true),
		);
	});

	it("lists children and flags the ones without a birthdate", async () => {
		mockChildren([aubrey, sophia]);

		renderWithQueryClient(<CircleBirthdayAlbumSetting circleId={7} enabled />);

		expect(await screen.findByLabelText("Sophia's birthdate")).toHaveValue(
			"2023-10-16",
		);
		expect(screen.getByLabelText("Aubrey's birthdate")).toHaveValue("");
		expect(
			screen.getAllByText("No birthdate yet, so their birthdays are skipped"),
		).toHaveLength(1);
	});

	it("says when the circle has no children", async () => {
		mockChildren([]);

		renderWithQueryClient(<CircleBirthdayAlbumSetting circleId={7} enabled />);

		expect(
			await screen.findByText("This circle has no children yet."),
		).toBeInTheDocument();
	});

	it("saves a missing birthdate", async () => {
		mockChildren([aubrey]);
		const save = vi
			.spyOn(circleServices, "updateChildBirthdate")
			.mockResolvedValue({
				data: { child: { ...aubrey, birthdate: "2026-06-10" } },
			});

		renderWithQueryClient(<CircleBirthdayAlbumSetting circleId={7} enabled />);
		const input = await screen.findByLabelText("Aubrey's birthdate");
		const button = screen.getByRole("button", { name: "Save" });
		expect(button).toBeDisabled();

		fireEvent.change(input, { target: { value: "2026-06-10" } });
		await act(async () => fireEvent.click(button));

		expect(save).toHaveBeenCalledWith("c2", "2026-06-10");
		await waitFor(() =>
			expect(
				screen.queryByText("No birthdate yet, so their birthdays are skipped"),
			).toBeNull(),
		);
	});
});
