import "@/i18n/config";

import { renderWithQueryClient } from "@/test-utils";
import { fireEvent, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { InvitationAcceptContent } from "./accept";

const mockUseInvitationAcceptance = vi.fn();

vi.mock("@/features/circles/hooks/useInvitationAcceptance", () => ({
	useInvitationAcceptance: (...args: unknown[]) =>
		mockUseInvitationAcceptance(...args),
}));

vi.mock("@tanstack/react-router", async () => {
	const actual = await vi.importActual<typeof import("@tanstack/react-router")>(
		"@tanstack/react-router",
	);
	return {
		...actual,
		useLocation: () => ({ pathname: "/invitations/accept" }),
	};
});

const navigateMock = vi.fn();

vi.mock("@/routes/invitations.accept", () => ({
	Route: {
		useNavigate: () => navigateMock,
		useSearch: () => ({ token: "abc" }),
	},
}));

describe("InvitationAcceptContent", () => {
	beforeEach(() => {
		vi.clearAllMocks();
		mockUseInvitationAcceptance.mockReturnValue({
			viewState: "invalid",
			invitationDetails: null,
			errorMessage: null,
			isLoading: false,
			mutations: {
				finalizePending: false,
				respondPending: false,
			},
			handleAccept: vi.fn(),
			handleDecline: vi.fn(),
		});
	});

	it("renders invalid state message", () => {
		renderWithQueryClient(<InvitationAcceptContent token={undefined} />);

		expect(
			screen.getByText("This invitation link is invalid or has expired."),
		).toBeInTheDocument();
	});

	it("shows invitation details when pending", () => {
		mockUseInvitationAcceptance.mockReturnValue({
			viewState: "pending",
			invitationDetails: {
				id: "inv-1",
				email: "user@example.com",
				existing_user: false,
				role: "member",
				circle: { id: 1, name: "Family", slug: "family", member_count: 2 },
				invited_user_id: null,
		invited_by: { display_name: "Alex", email: "alex@example.com" },
				reminder_scheduled_at: null,
			},
			errorMessage: null,
			isLoading: false,
			mutations: {
				finalizePending: false,
				respondPending: false,
			},
			handleAccept: vi.fn(),
			handleDecline: vi.fn(),
		});

		renderWithQueryClient(<InvitationAcceptContent token="abc" />);

		expect(screen.getByText("Join Family")).toBeInTheDocument();
		expect(screen.getByRole("button", { name: /accept/i })).toBeEnabled();
	});

	it("invokes accept handler when clicking accept button", () => {
		const acceptSpy = vi.fn();
		mockUseInvitationAcceptance.mockReturnValue({
			viewState: "pending",
			invitationDetails: {
				id: "inv-1",
				email: "user@example.com",
				existing_user: true,
				role: "member",
				circle: { id: 1, name: "Family", slug: "family", member_count: 2 },
				invited_user_id: 42,
		invited_by: { display_name: "Alex", email: "alex@example.com" },
				reminder_scheduled_at: null,
			},
			errorMessage: null,
			isLoading: false,
			mutations: {
				finalizePending: false,
				respondPending: false,
			},
			handleAccept: acceptSpy,
			handleDecline: vi.fn(),
		});

		renderWithQueryClient(<InvitationAcceptContent token="abc" />);

		fireEvent.click(screen.getByRole("button", { name: /accept/i }));
		expect(acceptSpy).toHaveBeenCalled();
	});
});
