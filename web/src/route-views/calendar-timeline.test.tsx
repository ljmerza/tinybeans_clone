import "@/i18n/config";
import { renderWithQueryClient } from "@/test-utils";
import { act, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import type { PhotoCalendarProps } from "react-photo-calendar";
import { afterEach, describe, expect, it, vi } from "vitest";

// The timeline itself is tested in react-photo-calendar; here a stub captures
// the props so the test can play the timeline's callbacks.
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

afterEach(() => {
	vi.restoreAllMocks();
	navigate.mockReset();
	calendarProps = undefined;
});

function renderCalendar() {
	vi.spyOn(circleServices, "listMemberships").mockResolvedValue(
		// biome-ignore lint/suspicious/noExplicitAny: memberships are irrelevant here
		{ data: { circles: [] } } as any,
	);
	const getCalendarMonth = vi
		.spyOn(keepServices, "getCalendarMonth")
		.mockImplementation(async (month: string) => ({
			data: {
				month,
				circle_slug: "family",
				entries: [
					{
						keep_id: `keep-${month}`,
						datetime: `${month}-04T00:00:00+00:00`,
						photos: [`https://cdn.test/${month}.jpg`],
					},
				],
			},
			messages: [],
		}));
	renderWithQueryClient(<CalendarRouteView />);
	return getCalendarMonth;
}

async function waitForCalendar() {
	await waitFor(() => expect(calendarProps?.entries).toHaveLength(1));
	return calendarProps as PhotoCalendarProps;
}

describe("CalendarRouteView timeline", () => {
	it("fetches the months in view and passes all their photos", async () => {
		const getCalendarMonth = renderCalendar();
		const props = await waitForCalendar();
		expect(props.navigationMode).toBe("auto");

		act(() => props.onMonthsInViewChange?.(["2026-06", "2026-07"]));

		await waitFor(() =>
			expect(calendarProps?.entries?.map((entry) => entry.photos[0])).toEqual([
				"https://cdn.test/2026-07.jpg",
				"https://cdn.test/2026-06.jpg",
			]),
		);
		expect(getCalendarMonth).toHaveBeenCalledWith("2026-06", "family");
	});

	it("opens the day feed for a day in a neighbouring month", async () => {
		renderCalendar();
		const props = await waitForCalendar();
		act(() => props.onMonthsInViewChange?.(["2026-06", "2026-07"]));
		await waitFor(() => expect(calendarProps?.entries).toHaveLength(2));

		act(() =>
			calendarProps?.onDaySelect?.({
				isoDate: "2026-06-04",
				date: new Date("2026-06-04T00:00:00Z"),
			}),
		);

		expect(navigate).toHaveBeenCalledWith({
			to: "/calendar/$date",
			params: { date: "2026-06-04" },
			search: { circle: "family" },
		});
	});

	it("replaces ?month= once a scrolled-to month has loaded", async () => {
		renderCalendar();
		const props = await waitForCalendar();

		act(() => props.onMonthChange?.("2026-05", { source: "scroll" }));

		await waitFor(() => expect(navigate).toHaveBeenCalledTimes(1));
		const call = navigate.mock.calls[0][0];
		expect(call).toMatchObject({
			to: "/calendar",
			replace: true,
			resetScroll: false,
		});
		expect(call.search({ month: "2026-07", circle: "family" })).toEqual({
			month: "2026-05",
			circle: "family",
		});
	});

	it("writes only the latest month when the timeline moves on before data arrives", async () => {
		renderCalendar();
		const props = await waitForCalendar();

		act(() => {
			props.onMonthChange?.("2026-05", { source: "scroll" });
			props.onMonthChange?.("2026-04", { source: "scroll" });
		});

		await waitFor(() => expect(navigate).toHaveBeenCalled());
		await new Promise((resolve) => setTimeout(resolve, 20));
		expect(navigate).toHaveBeenCalledTimes(1);
		expect(navigate.mock.calls[0][0].search({}).month).toBe("2026-04");
	});

	it("pushes a history entry for the month arrows as before", async () => {
		renderCalendar();
		const props = await waitForCalendar();

		act(() => props.onMonthChange?.("2026-08", { source: "navigation" }));

		expect(navigate).toHaveBeenCalledWith({
			to: "/calendar",
			search: { month: "2026-08", circle: "family" },
		});
	});
});
