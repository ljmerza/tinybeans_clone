import "@/i18n/config";
import { renderWithQueryClient } from "@/test-utils";
import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

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
	const mod = await importOriginal();
	return {
		...mod,
		useCircleMembers: vi.fn(),
	};
});

import { AuthSessionProvider } from "@/features/auth";
import { useCircleMembers } from "@/features/circles";
import { CircleDashboard } from "./dashboard";

describe("CircleDashboard", () => {
	beforeEach(() => {
		(useCircleMembers as unknown as vi.Mock).mockReset();
	});

	it("renders without hook errors", () => {
		(useCircleMembers as unknown as vi.Mock)
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
});
