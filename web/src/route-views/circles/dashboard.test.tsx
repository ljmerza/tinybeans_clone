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

import { aiAssistServices } from "@/features/aiAssist";
import { apiTokenServices } from "@/features/apiTokens";
import { AuthSessionProvider, authKeys, setAccessToken } from "@/features/auth";
import { useCircleMembers } from "@/features/circles";
import { createTestQueryClient } from "@/lib/query/queryClient";
import { CircleDashboard } from "./dashboard";

describe("CircleDashboard", () => {
	beforeEach(() => {
		(useCircleMembers as unknown as Mock).mockReset();
		vi.spyOn(aiAssistServices, "getSettings").mockResolvedValue({
			available: true,
			enabled: false,
			acknowledged_at: null,
			last_run_at: null,
			last_success_at: null,
			last_error: "",
			pending_count: 0,
		});
		vi.spyOn(apiTokenServices, "list").mockResolvedValue({
			agent_api_enabled: true,
			tokens: [],
		});
	});

	afterEach(() => {
		setAccessToken(null);
		// Not restoreAllMocks: that would also undo the useCircleMembers mock.
		vi.mocked(aiAssistServices.getSettings).mockRestore();
		vi.mocked(apiTokenServices.list).mockRestore();
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

	it("shows circle admins the Birthdays album switch", () => {
		renderAs("admin");

		expect(
			screen.getByRole("switch", { name: "Birthdays album" }),
		).not.toBeChecked();
	});

	it("hides the Birthdays album switch from members", () => {
		renderAs("member");

		expect(
			screen.queryByRole("switch", { name: "Birthdays album" }),
		).toBeNull();
	});

	it("shows circle admins the AI and API token settings", async () => {
		renderAs("admin");

		expect(
			screen.getByRole("switch", { name: "Review AI milestone picks" }),
		).not.toBeChecked();
		expect(
			await screen.findByRole("switch", { name: "AI milestone suggestions" }),
		).toBeInTheDocument();
		expect(
			screen.getByRole("heading", { name: "API tokens" }),
		).toBeInTheDocument();
		expect(await screen.findByText("No tokens yet.")).toBeInTheDocument();
	});

	it("hides the AI and API token settings from members", () => {
		renderAs("member");

		expect(
			screen.queryByRole("switch", { name: "Review AI milestone picks" }),
		).toBeNull();
		expect(screen.queryByRole("heading", { name: "API tokens" })).toBeNull();
		expect(aiAssistServices.getSettings).not.toHaveBeenCalled();
		expect(apiTokenServices.list).not.toHaveBeenCalled();
	});
});
