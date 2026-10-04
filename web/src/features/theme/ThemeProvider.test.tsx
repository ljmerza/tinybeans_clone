import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ThemeProvider, useTheme } from "./ThemeProvider";

const root = document.documentElement;

beforeEach(() => {
	// jsdom doesn't implement matchMedia.
	window.matchMedia = vi.fn().mockReturnValue({
		matches: false,
		addEventListener: vi.fn(),
		removeEventListener: vi.fn(),
	});
});

afterEach(() => {
	vi.restoreAllMocks();
	window.localStorage.clear();
	root.classList.remove("dark");
	root.removeAttribute("data-color-theme");
});

function ShowTheme() {
	const { preference, colorTheme } = useTheme();
	return (
		<p>
			{preference}/{colorTheme}
		</p>
	);
}

function renderTheme() {
	render(
		<ThemeProvider>
			<ShowTheme />
		</ThemeProvider>,
	);
}

describe("ThemeProvider storage keys", () => {
	it("moves a theme saved under the pre-rename tinybeans.* keys", () => {
		window.localStorage.setItem("tinybeans.themePreference", "dark");
		window.localStorage.setItem("tinybeans.colorTheme", "sage");

		renderTheme();

		expect(screen.getByText("dark/sage")).toBeInTheDocument();
		expect(root).toHaveClass("dark");
		expect(root).toHaveAttribute("data-color-theme", "sage");
		expect(window.localStorage.getItem("circles.themePreference")).toBe("dark");
		expect(window.localStorage.getItem("circles.colorTheme")).toBe("sage");
		expect(window.localStorage.getItem("tinybeans.themePreference")).toBeNull();
		expect(window.localStorage.getItem("tinybeans.colorTheme")).toBeNull();
	});

	it("prefers the circles.* keys over leftover legacy values", () => {
		window.localStorage.setItem("circles.themePreference", "light");
		window.localStorage.setItem("circles.colorTheme", "rose");
		window.localStorage.setItem("tinybeans.themePreference", "dark");
		window.localStorage.setItem("tinybeans.colorTheme", "sage");

		renderTheme();

		expect(screen.getByText("light/rose")).toBeInTheDocument();
		expect(window.localStorage.getItem("circles.themePreference")).toBe(
			"light",
		);
		expect(window.localStorage.getItem("circles.colorTheme")).toBe("rose");
	});

	it("falls back to the defaults when nothing is saved", () => {
		renderTheme();

		expect(screen.getByText("system/default")).toBeInTheDocument();
		expect(window.localStorage.getItem("circles.themePreference")).toBe(
			"system",
		);
		expect(window.localStorage.getItem("circles.colorTheme")).toBe("default");
	});
});
