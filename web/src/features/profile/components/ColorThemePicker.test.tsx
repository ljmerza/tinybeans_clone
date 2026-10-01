import { ThemeProvider } from "@/features/theme";
import { renderWithQueryClient } from "@/test-utils";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { profileServices } from "../api/services";
import { ColorThemePicker } from "./ColorThemePicker";

const root = document.documentElement;

beforeEach(() => {
	// ThemeProvider asks for the OS color scheme, which jsdom doesn't implement.
	window.matchMedia = vi.fn().mockReturnValue({
		matches: false,
		addEventListener: vi.fn(),
		removeEventListener: vi.fn(),
	});
});

afterEach(() => {
	vi.restoreAllMocks();
	window.localStorage.clear();
	root.removeAttribute("data-color-theme");
});

function renderPicker() {
	renderWithQueryClient(
		<ThemeProvider>
			<ColorThemePicker />
		</ThemeProvider>,
	);
}

describe("ColorThemePicker", () => {
	it("applies the palette and saves it to the profile", async () => {
		const update = vi
			.spyOn(profileServices, "updateProfile")
			.mockResolvedValue({
				data: { user: { id: 1, email: "a@b.c", color_theme: "sage" } },
			});

		renderPicker();
		expect(screen.getByRole("radio", { name: "Default" })).toBeChecked();
		expect(root).not.toHaveAttribute("data-color-theme");

		fireEvent.click(screen.getByRole("radio", { name: "Sage" }));

		await waitFor(() =>
			expect(update).toHaveBeenCalledWith(
				{ color_theme: "sage" },
				expect.objectContaining({ suppressSuccessToast: true }),
			),
		);
		expect(root).toHaveAttribute("data-color-theme", "sage");
		expect(window.localStorage.getItem("tinybeans.colorTheme")).toBe("sage");
		expect(screen.getByRole("radio", { name: "Sage" })).toBeChecked();
	});

	it("drops the attribute when switching back to the default palette", async () => {
		window.localStorage.setItem("tinybeans.colorTheme", "rose");
		vi.spyOn(profileServices, "updateProfile").mockResolvedValue({
			data: { user: { id: 1, email: "a@b.c", color_theme: "default" } },
		});

		renderPicker();
		await waitFor(() =>
			expect(root).toHaveAttribute("data-color-theme", "rose"),
		);

		fireEvent.click(screen.getByRole("radio", { name: "Default" }));

		await waitFor(() => expect(root).not.toHaveAttribute("data-color-theme"));
	});

	it("restores the previous palette when the save fails", async () => {
		vi.spyOn(console, "error").mockImplementation(() => {});
		const update = vi
			.spyOn(profileServices, "updateProfile")
			.mockRejectedValue(new Error("network down"));

		renderPicker();
		fireEvent.click(screen.getByRole("radio", { name: "Midnight" }));

		await waitFor(() => expect(update).toHaveBeenCalled());
		await waitFor(() => expect(root).not.toHaveAttribute("data-color-theme"));
		expect(screen.getByRole("radio", { name: "Default" })).toBeChecked();
		expect(window.localStorage.getItem("tinybeans.colorTheme")).toBe("default");
	});
});
