import "@/i18n/config";
import { renderWithQueryClient } from "@/test-utils";
import { fireEvent, screen, within } from "@testing-library/react";
import type { Mock } from "vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";

const navigate = vi.fn();
let pathname = "/profile/circles";

// No RouterProvider here: render <Link> as a plain anchor and stub the hooks
// ProfileSettingsTabs reads the active tab from.
vi.mock("@tanstack/react-router", async (importOriginal) => {
	const actual =
		await importOriginal<typeof import("@tanstack/react-router")>();
	return {
		...actual,
		useNavigate: () => navigate,
		useRouterState: ({
			select,
		}: {
			select: (state: { location: { pathname: string } }) => unknown;
		}) => select({ location: { pathname } }),
		Link: ({
			children,
			to,
			params,
			...rest
		}: {
			children?: React.ReactNode;
			to?: string;
			params?: Record<string, string>;
		}) => (
			<a href={to?.replace("$circleId", params?.circleId ?? "")} {...rest}>
				{children}
			</a>
		),
	};
});

vi.mock("@/features/circles", async (importOriginal) => {
	const mod = await importOriginal<typeof import("@/features/circles")>();
	return {
		...mod,
		useCircleMemberships: vi.fn(),
		useCircleRemoveSelfMutation: () => ({
			isPending: false,
			mutateAsync: vi.fn(),
		}),
	};
});

import { AuthSessionProvider } from "@/features/auth";
import { useCircleMemberships } from "@/features/circles";
import type { ReactNode } from "react";
import { ProfileCirclesSettings } from "./ProfileCirclesSettings";
import { ProfileSettingsTabs } from "./ProfileSettingsTabs";

const memberships = [
	{
		membership_id: 1,
		role: "admin",
		is_owner: true,
		circle: { id: 7, name: "Family", member_count: 3 },
	},
	{
		membership_id: 2,
		role: "member",
		is_owner: false,
		circle: { id: 9, name: "Friends", member_count: 5 },
	},
];

const withSession = (children: ReactNode) => (
	<AuthSessionProvider>{children}</AuthSessionProvider>
);

function mockMemberships(data: unknown[]) {
	(useCircleMemberships as unknown as Mock).mockReturnValue({
		data,
		isLoading: false,
		error: null,
		refetch: vi.fn(),
		isFetching: false,
	});
}

describe("ProfileCirclesSettings", () => {
	beforeEach(() => {
		navigate.mockReset();
		pathname = "/profile/circles";
		(useCircleMemberships as unknown as Mock).mockReset();
	});

	it("lists circles with their controls and no page title header", () => {
		mockMemberships(memberships);
		renderWithQueryClient(<ProfileCirclesSettings />, { wrapper: withSession });

		expect(screen.getByText("Family")).toBeInTheDocument();
		expect(screen.getByText("Friends")).toBeInTheDocument();
		expect(
			screen.getByRole("link", { name: "Open dashboard" }),
		).toHaveAttribute("href", "/circles/7");
		expect(
			screen.getByRole("button", { name: "Leave circle" }),
		).toBeInTheDocument();
		expect(screen.queryByRole("heading", { level: 1 })).not.toBeInTheDocument();
	});

	it("offers to create a circle when there are none", () => {
		mockMemberships([]);
		renderWithQueryClient(<ProfileCirclesSettings />, { wrapper: withSession });

		expect(
			screen.getByRole("link", { name: "Start onboarding" }),
		).toHaveAttribute("href", "/circles/onboarding");
	});

	it("shows as the active Circles tab on /profile/circles", () => {
		mockMemberships(memberships);
		renderWithQueryClient(
			<ProfileSettingsTabs
				general={<div>general content</div>}
				circles={<ProfileCirclesSettings />}
				twoFactor={null}
			/>,
			{ wrapper: withSession },
		);

		const tab = screen.getByRole("tab", { name: "Circles" });
		expect(tab).toHaveAttribute("aria-selected", "true");
		const panel = screen.getByRole("tabpanel");
		expect(within(panel).getByText("Family")).toBeInTheDocument();
		expect(screen.queryByText("general content")).not.toBeInTheDocument();
	});

	it("navigates to /profile/circles from another settings tab", () => {
		pathname = "/profile/general";
		renderWithQueryClient(
			<ProfileSettingsTabs
				general={<div>general content</div>}
				twoFactor={null}
			/>,
		);

		fireEvent.mouseDown(screen.getByRole("tab", { name: "Circles" }), {
			button: 0,
		});
		expect(navigate).toHaveBeenCalledWith({ to: "/profile/circles" });
	});
});
