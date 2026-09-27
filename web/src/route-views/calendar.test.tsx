import "@/i18n/config";
import { renderWithQueryClient } from "@/test-utils";
import { fireEvent, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

// Layout pulls in the auth session and router; this suite only cares about the
// calendar inside it.
vi.mock("@/components", async (importOriginal) => {
	const actual = await importOriginal<typeof import("@/components")>();
	const Layout = ({ children }: { children?: ReactNode }) => (
		<main>{children}</main>
	);
	Layout.Loading = ({ message }: { message?: string }) => <p>{message}</p>;
	Layout.Error = ({ title }: { title?: string }) => <p>{title}</p>;
	return { ...actual, Layout };
});

const navigate = vi.fn();

vi.mock("@tanstack/react-router", async (importOriginal) => ({
	...(await importOriginal<typeof import("@tanstack/react-router")>()),
	getRouteApi: () => ({
		useSearch: () => ({ month: "2026-07", circle: "family" }),
	}),
	useNavigate: () => navigate,
}));

import { circleServices } from "@/features/circles/api/services";
import { keepServices } from "@/features/keeps";
import { CalendarRouteView } from "./calendar";

afterEach(() => {
	vi.restoreAllMocks();
	navigate.mockReset();
});

async function renderCalendar() {
	vi.spyOn(circleServices, "listMemberships").mockResolvedValue(
		// biome-ignore lint/suspicious/noExplicitAny: memberships are irrelevant here
		{ data: { circles: [] } } as any,
	);
	vi.spyOn(keepServices, "getCalendarMonth").mockResolvedValue({
		data: {
			month: "2026-07",
			circle_slug: "family",
			entries: [
				{
					keep_id: "k1",
					datetime: "2026-07-04T00:00:00+00:00",
					photos: ["https://cdn.test/1.jpg"],
				},
			],
		},
		messages: [],
	});
	renderWithQueryClient(<CalendarRouteView />);
	return screen.findByRole("gridcell", { name: /\. 1 photo$/ });
}

describe("CalendarRouteView", () => {
	it("opens the day feed when a day with photos is clicked", async () => {
		fireEvent.click(await renderCalendar());

		expect(navigate).toHaveBeenCalledWith({
			to: "/calendar/$date",
			params: { date: "2026-07-04" },
			search: { circle: "family" },
		});
	});

	it("ignores clicks on days without photos", async () => {
		await renderCalendar();

		fireEvent.click(
			screen.getByRole("gridcell", {
				name: /(10 July|July 10,) 2026\. No photos/,
			}),
		);

		expect(navigate).not.toHaveBeenCalled();
	});
});
