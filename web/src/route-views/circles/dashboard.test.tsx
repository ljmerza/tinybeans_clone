import "@/i18n/config";
import { renderWithQueryClient } from "@/test-utils";
import { screen } from "@testing-library/react";
import type { Mock } from "vitest";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// The dashboard renders <Link>, which needs a RouterProvider this suite has no
// reason to build. Render it as a plain anchor instead.
vi.mock("@tanstack/react-router", async (importOriginal) => {
	const actual = await importOriginal<typeof import("@tanstack/react-router")>();
	return {
		...actual,
		Link: ({
			children,
			to,
			...rest
		}: {
			children?: React.ReactNode;
			to?: string;
		}) => (
			<a href={to} {...rest}>
				{children}
			</a>
		),
	};
});

vi.mock("@/features/circles", async (importOriginal) => {
	const mod = await importOriginal<typeof import("@/features/circles")>();
	return {
		...mod,
		useCircleMembers: vi.fn(),
	};
});

import { AuthSessionProvider, authKeys, setAccessToken } from "@/features/auth";
import { useCircleMembers } from "@/features/circles";
import { createTestQueryClient } from "@/lib/query/queryClient";
import { CircleDashboard } from "./dashboard";

describe("CircleDashboard", () => {
	beforeEach(() => {
		(useCircleMembers as unknown as Mock).mockReset();
	});

	afterEach(() => {
		setAccessToken(null);
	});

	it("renders without hook errors", () => {
		(useCircleMembers as unknown as Mock)
			.mockReturnValueOnce({
				data: undefined,
				isLoading: true,
				error: null,
				refetch: vi.fn(),
				isFetching: false,
			})
			.mockReturnValue({
				data: {
					circle: { id: 3, name: "Family", member_count: 2 },
					members: [],
				},
				isLoading: false,
				error: null,
				refetch: vi.fn(),
				isFetching: false,
			});

		renderWithQueryClient(
			<AuthSessionProvider>
				<CircleDashboard circleId="3" />
			</AuthSessionProvider>,
		);
		expect(useCircleMembers).toHaveBeenCalled();
	});

	/** Signed in as user 1, the circle's only member, with `role`. */
	function renderAs(role: "admin" | "member") {
		setAccessToken("access");
		const queryClient = createTestQueryClient();
		queryClient.setQueryData(authKeys.session(), { id: 1 });
		(useCircleMembers as unknown as Mock).mockReturnValue({
			data: {
				circle: {
					id: 3,
					name: "Family",
					slug: "family",
					member_count: 1,
					monthly_recap_enabled: true,
				},
				members: [
					{
						membership_id: 1,
						user: {
							id: 1,
							email: "leo@example.com",
							first_name: "Leo",
							last_name: "",
						},
						role,
						is_owner: role === "admin",
						created_at: "2026-01-01T00:00:00Z",
					},
				],
			},
			isLoading: false,
			error: null,
			refetch: vi.fn(),
			isFetching: false,
		});
		renderWithQueryClient(
			<AuthSessionProvider>
				<CircleDashboard circleId="3" />
			</AuthSessionProvider>,
			{ queryClient },
		);
	}

	it("shows circle admins the monthly recap switch", () => {
		renderAs("admin");

		expect(
			screen.getByRole("switch", { name: "Monthly recap album" }),
		).toBeChecked();
	});

	it("hides the monthly recap switch from members", () => {
		renderAs("member");

		expect(
			screen.queryByRole("switch", { name: "Monthly recap album" }),
		).toBeNull();
	});
});
