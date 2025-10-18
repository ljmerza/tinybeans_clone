import "@/i18n/config";

import { renderWithQueryClient } from "@/test-utils";
import { screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { InvitationAcceptContent } from "./accept";

const mockUseAuthSession = vi.fn();
const mockUseStartOnboarding = vi.fn();
const mockUseFinalizeInvitation = vi.fn();
const mockUseRespondInvitation = vi.fn();
const mockLoadInvitation = vi.fn();
const mockSubscribeInvitationStorage = vi.fn();

vi.mock("@/features/auth", () => ({
	useAuthSession: () => mockUseAuthSession(),
}));

vi.mock("@/features/circles/hooks/useCircleInvitationOnboarding", () => ({
	useStartCircleInvitationOnboarding: (...args: unknown[]) =>
		mockUseStartOnboarding(...args),
	useFinalizeCircleInvitation: (...args: unknown[]) =>
		mockUseFinalizeInvitation(...args),
	useRespondToCircleInvitation: (...args: unknown[]) =>
		mockUseRespondInvitation(...args),
}));

vi.mock("@/features/circles/utils/invitationStorage", () => ({
	loadInvitation: () => mockLoadInvitation(),
	subscribeInvitationStorage: (callback: unknown) =>
		mockSubscribeInvitationStorage(callback) ?? (() => undefined),
	clearInvitation: vi.fn(),
}));

vi.mock("@/features/circles/utils/inviteAnalytics", () => ({
	rememberInviteRedirect: vi.fn(),
}));

vi.mock("@tanstack/react-router", async () => {
	const actual = await vi.importActual<typeof import("@tanstack/react-router")>(
		"@tanstack/react-router",
	);
	return {
		...actual,
		useLocation: () => ({ pathname: "/invitations/accept", search: "?token=abc" }),
	};
});

const navigateMock = vi.fn();

vi.mock("@/routes/invitations.accept", () => ({
	Route: {
		useNavigate: () => navigateMock,
	},
}));

describe("InvitationAcceptContent", () => {
	beforeEach(() => {
		vi.clearAllMocks();
		mockUseAuthSession.mockReturnValue({
			status: "guest",
			accessToken: null,
			isAuthenticated: false,
			isGuest: true,
			isUnknown: false,
			user: null,
			isFetchingUser: false,
			userError: null,
			refetchUser: vi.fn(),
		});
		mockUseStartOnboarding.mockReturnValue({
			mutate: vi.fn(),
			isPending: false,
		});
		mockUseFinalizeInvitation.mockReturnValue({
			mutate: vi.fn(),
			isPending: false,
		});
		mockUseRespondInvitation.mockReturnValue({
			mutate: vi.fn(),
			isPending: false,
		});
		mockLoadInvitation.mockReturnValue(null);
		mockSubscribeInvitationStorage.mockReturnValue(() => undefined);
	});

	it("shows invalid state when no token or stored invitation", () => {
		renderWithQueryClient(<InvitationAcceptContent />);
		expect(
			screen.getByText("This invitation link is invalid or has expired."),
		).toBeInTheDocument();
	});

	it("renders pending state with sign-in prompt", () => {
		mockLoadInvitation.mockReturnValue({
			onboardingToken: "on-token",
			expiresInMinutes: 60,
			invitation: {
				id: "inv-1",
				email: "user@example.com",
				existing_user: false,
				role: "member",
				circle: { id: 1, name: "Family", slug: "family", member_count: 2 },
				invited_user_id: null,
				invited_by: null,
				reminder_scheduled_at: null,
			},
			sourceToken: "abc",
			redirectPath: "/invitations/accept?token=abc",
		});

		renderWithQueryClient(
			<InvitationAcceptContent token="abc" />,
		);

		expect(
			screen.getByText("Sign in or create an account to finish joining."),
		).toBeInTheDocument();
	});

	it("finalizes invitation when authenticated", async () => {
		mockLoadInvitation.mockReturnValue({
			onboardingToken: "stored-token",
			expiresInMinutes: 60,
			invitation: {
				id: "inv-1",
				email: "user@example.com",
				existing_user: true,
				role: "member",
				circle: { id: 1, name: "Family", slug: "family", member_count: 2 },
				invited_user_id: 99,
				invited_by: { username: "alex" },
				reminder_scheduled_at: null,
			},
			sourceToken: "abc",
			redirectPath: "/invitations/accept?token=abc",
		});

		const finalizeSpy = vi.fn((_: string, options?: { onSuccess?: () => void }) => {
			options?.onSuccess?.();
		});

		mockUseFinalizeInvitation.mockReturnValue({
			mutate: finalizeSpy,
			isPending: false,
		});

		mockUseAuthSession.mockReturnValue({
			status: "authenticated",
			accessToken: "token",
			isAuthenticated: true,
			isGuest: false,
			isUnknown: false,
			user: { id: 1, username: "alex" },
			isFetchingUser: false,
			userError: null,
			refetchUser: vi.fn(),
		});

		renderWithQueryClient(
			<InvitationAcceptContent token="abc" />,
		);

		await waitFor(() => {
			expect(finalizeSpy).toHaveBeenCalledWith(
				"stored-token",
				expect.objectContaining({ onSuccess: expect.any(Function) }),
			);
		});

		expect(
			screen.getByText("You're now a member of Family."),
		).toBeInTheDocument();
	});
});
