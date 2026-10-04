import "@/i18n/config";
import { renderWithQueryClient } from "@/test-utils";
import {
	act,
	fireEvent,
	screen,
	waitFor,
	within,
} from "@testing-library/react";
import type { ReactNode } from "react";
import type { PhotoCalendarProps } from "react-photo-calendar";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// The calendar is stubbed; its props are kept to play the timeline's scrolling.
let calendarProps: PhotoCalendarProps | undefined;
vi.mock("react-photo-calendar", () => ({
	PhotoCalendar: (props: PhotoCalendarProps) => {
		calendarProps = props;
		return null;
	},
}));

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

beforeEach(() => {
	// Only Date: real timers keep the query and dialog promises moving.
	vi.useFakeTimers({ toFake: ["Date"] });
	vi.setSystemTime(new Date(2026, 7, 15));
});

afterEach(() => {
	vi.useRealTimers();
	vi.restoreAllMocks();
	navigate.mockReset();
	calendarProps = undefined;
});

async function openMonthJump() {
	vi.spyOn(circleServices, "listMemberships").mockResolvedValue(
		// biome-ignore lint/suspicious/noExplicitAny: memberships are irrelevant here
		{ data: { circles: [] } } as any,
	);
	const getCalendarMonth = vi
		.spyOn(keepServices, "getCalendarMonth")
		.mockImplementation(async (month: string) => ({
			data: { month, circle_slug: "family", entries: [] },
			messages: [],
		}));
	renderWithQueryClient(<CalendarRouteView />);
	fireEvent.click(
		await screen.findByRole("button", {
			name: /Jump to month, showing July 2026/,
		}),
	);
	const dialog = await screen.findByRole("dialog", { name: "Jump to month" });
	return Object.assign(within(dialog), { getCalendarMonth });
}

describe("CalendarRouteView month jump", () => {
	it("navigates to the chosen month and keeps the circle", async () => {
		const dialog = await openMonthJump();

		fireEvent.click(dialog.getByRole("button", { name: "Previous year" }));
		fireEvent.click(dialog.getByRole("button", { name: "Previous year" }));
		fireEvent.click(dialog.getByRole("button", { name: "March 2024" }));

		expect(navigate).toHaveBeenCalledWith({
			to: "/calendar",
			search: { month: "2024-03", circle: "family" },
		});
		expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
	});

	it("does not offer future months", async () => {
		const dialog = await openMonthJump();

		expect(dialog.getByRole("button", { name: "August 2026" })).toBeEnabled();
		expect(
			dialog.getByRole("button", { name: "September 2026" }),
		).toBeDisabled();
		expect(
			dialog.getByRole("button", { name: "December 2026" }),
		).toBeDisabled();
		expect(dialog.getByRole("button", { name: "Next year" })).toBeDisabled();
		expect(
			dialog.getByRole("button", { name: "July 2026", pressed: true }),
		).toBeInTheDocument();
	});

	it("stops at the start of the timeline, ten years back", async () => {
		const dialog = await openMonthJump();

		for (let step = 0; step < 10; step += 1) {
			fireEvent.click(dialog.getByRole("button", { name: "Previous year" }));
		}

		expect(dialog.getByText("2016")).toBeInTheDocument();
		expect(
			dialog.getByRole("button", { name: "Previous year" }),
		).toBeDisabled();
		expect(dialog.getByRole("button", { name: "July 2016" })).toBeDisabled();
		expect(dialog.getByRole("button", { name: "August 2016" })).toBeEnabled();
	});

	it("jumps back to the current month with Today", async () => {
		const dialog = await openMonthJump();

		fireEvent.click(dialog.getByRole("button", { name: "Today" }));

		expect(navigate).toHaveBeenCalledWith({
			to: "/calendar",
			search: { month: "2026-08", circle: "family" },
		});
	});

	it("does not navigate when the shown month is picked again", async () => {
		const dialog = await openMonthJump();

		fireEvent.click(dialog.getByRole("button", { name: "July 2026" }));

		expect(navigate).not.toHaveBeenCalled();
		expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
	});

	it("matches the timeline's reach and cancels a scroll sync still loading", async () => {
		const dialog = await openMonthJump();
		const props = calendarProps as PhotoCalendarProps;
		expect(props.virtualRange).toEqual({ before: 120 });

		// The timeline settles on May, but May's data is still on its way.
		let finishMay = () => {};
		dialog.getCalendarMonth.mockImplementationOnce(
			(month: string) =>
				new Promise((resolve) => {
					finishMay = () =>
						resolve({
							data: { month, circle_slug: "family", entries: [] },
							messages: [],
						});
				}),
		);
		act(() => props.onMonthChange?.("2026-05", { source: "scroll" }));

		fireEvent.click(dialog.getByRole("button", { name: "Previous year" }));
		fireEvent.click(dialog.getByRole("button", { name: "March 2025" }));
		await act(async () => {
			finishMay();
			await new Promise((resolve) => setTimeout(resolve, 20));
		});

		expect(navigate).toHaveBeenCalledTimes(1);
		expect(navigate).toHaveBeenCalledWith({
			to: "/calendar",
			search: { month: "2025-03", circle: "family" },
		});
	});

	it("opens from a tapped month header, on that month's year", async () => {
		const dialog = await openMonthJump();
		fireEvent.click(dialog.getByRole("button", { name: "Close" }));
		await waitFor(() =>
			expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
		);

		expect(calendarProps?.monthHeaderLabel?.("March 2024", "2024-03")).toBe(
			"March 2024, jump to another month",
		);
		act(() => calendarProps?.onMonthHeaderClick?.("2024-03"));

		const fromHeader = within(
			await screen.findByRole("dialog", { name: "Jump to month" }),
		);
		expect(fromHeader.getByText("2024")).toBeInTheDocument();
		fireEvent.click(fromHeader.getByRole("button", { name: "Close" }));
		await waitFor(() =>
			expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
		);

		// The button above the timeline opens on the current month's year again.
		fireEvent.click(
			screen.getByRole("button", { name: /Jump to month, showing July 2026/ }),
		);
		const fromButton = within(
			await screen.findByRole("dialog", { name: "Jump to month" }),
		);
		expect(fromButton.getByText("2026")).toBeInTheDocument();
	});
});
