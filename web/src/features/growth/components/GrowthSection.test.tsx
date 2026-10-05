import "@/i18n/config";
import { setAccessToken } from "@/features/auth";
import { renderWithQueryClient } from "@/test-utils";
import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { growthServices } from "../api/services";
import {
	makeGrowthLog,
	makeMeasurement,
	mockSignedInUser,
	withSession,
} from "../testData";
import type { GrowthLog } from "../types";
import type { MeasurementUnits } from "../utils/units";
import { GrowthSection } from "./GrowthSection";

const PERSON_ID = "bbbbbbbb-0000-0000-0000-000000000001";

const june = makeMeasurement();
const march = makeMeasurement({
	id: "cccccccc-0000-0000-0000-000000000002",
	measured_on: "2025-03-01",
	height_cm: null,
	weight_kg: 5.4,
	note: "Checkup",
});

afterEach(() => {
	vi.restoreAllMocks();
	setAccessToken(null);
});

function renderSection(
	log: Partial<GrowthLog>,
	units: MeasurementUnits = "imperial",
) {
	const account = mockSignedInUser(units);
	vi.spyOn(growthServices, "getLog").mockResolvedValue(
		makeGrowthLog({ measurements: [march, june], ...log }),
	);
	renderWithQueryClient(<GrowthSection personId={PERSON_ID} name="Sophia" />, {
		wrapper: withSession,
	});
	return account;
}

const list = () => screen.findByRole("list", { name: "Measurements" });

describe("GrowthSection", () => {
	it("shows members the log in imperial, newest first, with no admin controls", async () => {
		renderSection({ can_edit: false });

		const rows = within(await list()).getAllByRole("listitem");
		expect(rows).toHaveLength(2);
		expect(rows[0]).toHaveTextContent("Jun 1, 2025");
		expect(rows[0]).toHaveTextContent("4 mo");
		expect(rows[0]).toHaveTextContent("2 ft 0.2 in · 13 lb 13 oz");
		expect(rows[1]).toHaveTextContent("11 lb 14.5 oz");
		expect(rows[1]).toHaveTextContent("Checkup");
		expect(
			screen.getByRole("img", { name: "Sophia's weight over time" }),
		).toBeInTheDocument();

		expect(
			screen.queryByRole("button", { name: "Add" }),
		).not.toBeInTheDocument();
		expect(
			screen.queryByRole("button", { name: /Edit the measurement/ }),
		).not.toBeInTheDocument();
		expect(
			screen.queryByRole("button", { name: /Delete the measurement/ }),
		).not.toBeInTheDocument();
	});

	it("gives circle admins add, edit and delete", async () => {
		renderSection({ can_edit: true });

		await list();
		expect(screen.getByRole("button", { name: "Add" })).toBeInTheDocument();
		expect(
			screen.getByRole("button", {
				name: "Edit the measurement from Jun 1, 2025",
			}),
		).toBeInTheDocument();
		expect(
			screen.getByRole("button", {
				name: "Delete the measurement from Mar 1, 2025",
			}),
		).toBeInTheDocument();
	});

	it("starts in metric for a user who chose it", async () => {
		renderSection({}, "metric");

		await waitFor(async () =>
			expect(
				within(await list()).getAllByRole("listitem")[0],
			).toHaveTextContent("61.5 cm · 6.265 kg"),
		);
		expect(screen.getByRole("radio", { name: "kg · cm" })).toBeChecked();
	});

	it("switches units on the spot and saves the choice to the account", async () => {
		const { updateProfile } = renderSection({});
		const firstRow = async () =>
			within(await list()).getAllByRole("listitem")[0];
		expect(await firstRow()).toHaveTextContent("13 lb 13 oz");
		expect(screen.getByRole("radio", { name: "lb · in" })).toBeChecked();

		fireEvent.click(screen.getByRole("radio", { name: "kg · cm" }));

		expect(await firstRow()).toHaveTextContent("61.5 cm · 6.265 kg");
		await waitFor(() =>
			expect(updateProfile).toHaveBeenCalledWith(
				{ measurement_units: "metric" },
				expect.objectContaining({ suppressSuccessToast: true }),
			),
		);
		await waitFor(() =>
			expect(screen.getByRole("radio", { name: "kg · cm" })).toBeChecked(),
		);
	});

	it("goes back to the previous units when saving them fails", async () => {
		const { updateProfile } = renderSection({});
		vi.spyOn(console, "error").mockImplementation(() => {});
		updateProfile.mockRejectedValue(new Error("network down"));
		await list();

		fireEvent.click(screen.getByRole("radio", { name: "kg · cm" }));

		await waitFor(() => expect(updateProfile).toHaveBeenCalled());
		await waitFor(() =>
			expect(screen.getByRole("radio", { name: "lb · in" })).toBeChecked(),
		);
	});

	it("adds a measurement typed in pounds and ounces as kilograms", async () => {
		renderSection({ can_edit: true, measurements: [] });
		const create = vi
			.spyOn(growthServices, "create")
			.mockResolvedValue(makeMeasurement({ id: "new", weight_kg: 3.402 }));

		fireEvent.click(await screen.findByRole("button", { name: "Add" }));
		const dialog = await screen.findByRole("dialog");
		fireEvent.change(within(dialog).getByLabelText("Date"), {
			target: { value: "2025-02-01" },
		});
		fireEvent.change(within(dialog).getByLabelText("Weight (lb)"), {
			target: { value: "7" },
		});
		fireEvent.change(within(dialog).getByLabelText("Weight (oz)"), {
			target: { value: "8" },
		});
		fireEvent.click(within(dialog).getByRole("button", { name: "Save" }));

		await waitFor(() =>
			expect(create).toHaveBeenCalledWith(PERSON_ID, {
				measured_on: "2025-02-01",
				height_cm: null,
				weight_kg: 3.402,
				note: "",
			}),
		);
	});

	it("asks for a height or a weight", async () => {
		renderSection({ can_edit: true, measurements: [] });
		const create = vi.spyOn(growthServices, "create");

		fireEvent.click(await screen.findByRole("button", { name: "Add" }));
		const dialog = await screen.findByRole("dialog");
		fireEvent.click(within(dialog).getByRole("button", { name: "Save" }));

		expect(await within(dialog).findByRole("alert")).toHaveTextContent(
			"Enter a height, a weight or both.",
		);
		expect(create).not.toHaveBeenCalled();
	});

	it("sends only the changed value when editing, so the other doesn't drift", async () => {
		renderSection({ can_edit: true });
		const update = vi
			.spyOn(growthServices, "update")
			.mockResolvedValue({ ...june, weight_kg: 6.35 });

		fireEvent.click(
			await screen.findByRole("button", {
				name: "Edit the measurement from Jun 1, 2025",
			}),
		);
		const dialog = await screen.findByRole("dialog");
		// Prefilled in imperial from the stored metric values.
		expect(within(dialog).getByLabelText("Height (ft)")).toHaveValue("2");
		expect(within(dialog).getByLabelText("Height (in)")).toHaveValue("0.2");
		expect(within(dialog).getByLabelText("Weight (oz)")).toHaveValue("13");
		fireEvent.change(within(dialog).getByLabelText("Weight (oz)"), {
			target: { value: "16" },
		});
		fireEvent.click(within(dialog).getByRole("button", { name: "Save" }));

		await waitFor(() =>
			expect(update).toHaveBeenCalledWith(PERSON_ID, june.id, {
				weight_kg: 6.35,
			}),
		);
	});

	it("deletes a measurement after confirming", async () => {
		renderSection({ can_edit: true });
		const remove = vi
			.spyOn(growthServices, "remove")
			.mockResolvedValue(undefined);

		fireEvent.click(
			await screen.findByRole("button", {
				name: "Delete the measurement from Mar 1, 2025",
			}),
		);
		const dialog = await screen.findByRole("alertdialog");
		fireEvent.click(within(dialog).getByRole("button", { name: "Delete" }));

		await waitFor(() =>
			expect(remove).toHaveBeenCalledWith(PERSON_ID, march.id),
		);
		await waitFor(() =>
			expect(
				within(screen.getByRole("list")).getAllByRole("listitem"),
			).toHaveLength(1),
		);
	});
});
