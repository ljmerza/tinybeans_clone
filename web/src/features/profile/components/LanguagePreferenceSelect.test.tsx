import i18n from "@/i18n/config";
import { renderWithQueryClient } from "@/test-utils";
import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { profileServices } from "../api/services";
import { LanguagePreferenceSelect } from "./LanguagePreferenceSelect";

beforeEach(async () => {
	// Radix Select scrolls the chosen option into view, which jsdom lacks.
	Element.prototype.scrollIntoView = vi.fn();
	await i18n.changeLanguage("en");
});

afterEach(async () => {
	vi.restoreAllMocks();
	// The component may still be mounted and re-renders on language change.
	await act(() => i18n.changeLanguage("en"));
});

async function chooseSpanish() {
	const trigger = await screen.findByRole("combobox", {
		name: "Display language",
	});
	expect(trigger).toHaveTextContent("English");
	// jsdom drops pointer event details, so open it the keyboard way.
	fireEvent.keyDown(trigger, { key: "ArrowDown" });
	fireEvent.click(await screen.findByRole("option", { name: "Español" }));
}

describe("LanguagePreferenceSelect", () => {
	it("switches the UI language and saves it to the profile", async () => {
		const update = vi
			.spyOn(profileServices, "updateProfile")
			.mockResolvedValue({
				data: { user: { id: 1, email: "a@b.c", language: "es" } },
			});

		renderWithQueryClient(<LanguagePreferenceSelect />);
		await chooseSpanish();

		await waitFor(() =>
			expect(update).toHaveBeenCalledWith(
				{ language: "es" },
				expect.objectContaining({ suppressSuccessToast: true }),
			),
		);
		expect(i18n.language).toBe("es");
		expect(
			await screen.findByRole("combobox", { name: "Idioma de la interfaz" }),
		).toHaveTextContent("Español");
	});

	it("reverts to the previous language when the save fails", async () => {
		vi.spyOn(console, "error").mockImplementation(() => {});
		const update = vi
			.spyOn(profileServices, "updateProfile")
			.mockRejectedValue(new Error("network down"));

		renderWithQueryClient(<LanguagePreferenceSelect />);
		await chooseSpanish();

		await waitFor(() => expect(update).toHaveBeenCalled());
		await waitFor(() => expect(i18n.language).toBe("en"));
		expect(
			await screen.findByRole("combobox", { name: "Display language" }),
		).toHaveTextContent("English");
	});
});
