import "@/i18n/config";
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@tanstack/react-router", async (importOriginal) => ({
	...(await importOriginal<typeof import("@tanstack/react-router")>()),
	Link: ({ children, to }: { children?: React.ReactNode; to?: string }) => (
		<a href={to}>{children}</a>
	),
}));

import { LandingPage } from "./LandingPage";

describe("LandingPage", () => {
	it("leads with the headline and sign-up and sign-in calls to action", () => {
		render(<LandingPage />);

		expect(
			screen.getByRole("heading", {
				level: 1,
				name: "Your family's moments, kept in one private circle",
			}),
		).toBeInTheDocument();
		const ctas = screen.getAllByRole("link", { name: "Create your circle" });
		expect(ctas.length).toBeGreaterThan(0);
		for (const cta of ctas) expect(cta).toHaveAttribute("href", "/signup");
		expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute(
			"href",
			"/login",
		);
	});

	it("lists six features, three steps and three privacy points", () => {
		render(<LandingPage />);

		const features = screen
			.getByRole("heading", {
				level: 2,
				name: "Everything your family needs to stay close",
			})
			.closest("section") as HTMLElement;
		expect(within(features).getAllByRole("listitem")).toHaveLength(6);

		const steps = screen
			.getByRole("heading", { level: 2, name: "How it works" })
			.closest("section") as HTMLElement;
		expect(within(steps).getAllByRole("listitem")).toHaveLength(3);

		const privacy = screen
			.getByRole("heading", { level: 2, name: "Private by design" })
			.closest("section") as HTMLElement;
		expect(within(privacy).getAllByRole("listitem")).toHaveLength(3);
	});

	it("keeps decorative icons out of the accessibility tree", () => {
		const { container } = render(<LandingPage />);

		for (const svg of container.querySelectorAll("svg")) {
			expect(svg.closest("[aria-hidden='true']")).not.toBeNull();
		}
	});
});
