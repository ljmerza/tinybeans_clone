import "@/i18n/config";

import { renderWithQueryClient } from "@/test-utils";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CircleInvitationList } from "./CircleInvitationList";

const mockUseCircleInvitationsQuery = vi.fn();
const mockUseResendCircleInvitation = vi.fn();
const mockUseCancelCircleInvitation = vi.fn();

vi.mock("../hooks/useCircleInvitationAdmin", () => ({
	useCircleInvitationsQuery: (...args: unknown[]) =>
		mockUseCircleInvitationsQuery(...args),
	useResendCircleInvitation: (...args: unknown[]) =>
		mockUseResendCircleInvitation(...args),
	useCancelCircleInvitation: (...args: unknown[]) =>
		mockUseCancelCircleInvitation(...args),
}));

describe("CircleInvitationList", () => {
	const resendSpy = vi.fn().mockResolvedValue({});
	const cancelSpy = vi.fn().mockResolvedValue({});

beforeEach(() => {
	resendSpy.mockClear();
	cancelSpy.mockClear();
	mockUseCircleInvitationsQuery.mockReturnValue({
			data: [
				{
					id: "invite-1",
					email: "alex@example.com",
					existing_user: true,
					role: "member",
					status: "pending",
					created_at: "2025-02-14T12:00:00Z",
					responded_at: null,
					reminder_sent_at: null,
					invited_user: null,
				},
				{
					id: "invite-2",
					email: "sarah@example.com",
					existing_user: false,
					role: "member",
					status: "accepted",
					created_at: "2025-02-10T12:00:00Z",
					responded_at: "2025-02-11T12:05:00Z",
					reminder_sent_at: null,
					invited_user: null,
				},
			],
			isFetching: false,
			isLoading: false,
			error: null,
			refetch: vi.fn(),
		});

		mockUseResendCircleInvitation.mockReturnValue({
			mutateAsync: resendSpy,
			isPending: false,
		});

		mockUseCancelCircleInvitation.mockReturnValue({
			mutateAsync: cancelSpy,
			isPending: false,
		});
	});

	it("renders invitation statuses and triggers resend action", async () => {
		renderWithQueryClient(<CircleInvitationList circleId="42" />);

		expect(
			screen.getByText("alex@example.com", { selector: "div" }),
		).toBeInTheDocument();
		expect(screen.getByText("Pending")).toBeInTheDocument();
		expect(screen.getByText("Existing account")).toBeInTheDocument();
		expect(screen.getByText("Accepted")).toBeInTheDocument();

		fireEvent.click(screen.getByRole("button", { name: "Resend" }));

		await waitFor(() => {
			expect(resendSpy).toHaveBeenCalledWith("invite-1");
		});
	});

	it("disables actions when invitation is not pending", () => {
		renderWithQueryClient(<CircleInvitationList circleId="42" />);
		const acceptedInvite = screen.getAllByRole("button", { name: "Resend" })[1];
		expect(acceptedInvite).toBeDisabled();
	});
});
