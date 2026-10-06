import "@/i18n/config";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@tanstack/react-router", async (importOriginal) => {
	const actual =
		await importOriginal<typeof import("@tanstack/react-router")>();
	return {
		...actual,
		Link: ({ children, to }: { children?: React.ReactNode; to?: string }) => (
			<a href={to}>{children}</a>
		),
	};
});

import { Header } from "./Header";

describe("Header", () => {
	it("shows the Circles brand linking home", () => {
		render(<Header isAuthenticated={false} />);

		expect(screen.getByRole("link", { name: "Circles" })).toHaveAttribute(
			"href",
			"/",
		);
	});

	it("has no Circles link; circles live under Settings", () => {
		render(<Header isAuthenticated />);

		// The only "Circles" link is the brand, which goes home.
		expect(screen.getByRole("link", { name: "Circles" })).toHaveAttribute(
			"href",
			"/",
		);
		expect(
			screen.queryByRole("link", {
				name: (_, el) => el.getAttribute("href") === "/circles",
			}),
		).not.toBeInTheDocument();
		expect(screen.getByRole("link", { name: "Settings" })).toHaveAttribute(
			"href",
			"/profile/general",
		);
	});

	it("links to the albums next to favorites", () => {
		render(<Header isAuthenticated />);

		const links = screen.getAllByRole("link").map((link) => link.textContent);
		expect(links.indexOf("Albums")).toBe(links.indexOf("Favorites") + 1);
		expect(screen.getByRole("link", { name: "Albums" })).toHaveAttribute(
			"href",
			"/albums",
		);
	});
});
