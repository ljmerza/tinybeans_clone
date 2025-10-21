import "@/i18n/config";

import { renderWithQueryClient } from "@/test-utils";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CircleInvitationList } from "./CircleInvitationList";

const mockUseCircleInvitationListController = vi.fn();

vi.mock("../hooks/useCircleInvitationListController", () => ({
	useCircleInvitationListController: (...args: unknown[]) =>
		mockUseCircleInvitationListController(...args),
}));

describe("CircleInvitationList", () => {
	const invitations = [
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
			invited_user: {
				id: 24,
				username: "sarah",
				first_name: "Sarah",
				last_name: "Doe",
			},
		},
	] as const;

	const resendSpy = vi.fn().mockResolvedValue({});
	const removeSpy = vi.fn().mockResolvedValue({});
	const openRemoveSpy = vi.fn();
	const cancelOpenSpy = vi.fn();
	const cancelCloseSpy = vi.fn();
	const cancelConfirmSpy = vi.fn();
	const removalCloseSpy = vi.fn();
	const removalCancelSpy = vi.fn();

	beforeEach(() => {
		resendSpy.mockClear();
		removeSpy.mockClear();
		openRemoveSpy.mockClear();
		cancelOpenSpy.mockClear();
		cancelCloseSpy.mockClear();
		cancelConfirmSpy.mockClear();
		removalCloseSpy.mockClear();
		removalCancelSpy.mockClear();
		cancelConfirmSpy.mockResolvedValue(undefined);

		mockUseCircleInvitationListController.mockReturnValue({
			invitations,
			query: {
				isFetching: false,
				isLoading: false,
				error: null,
				refetch: vi.fn(),
			},
			resend: {
				trigger: resendSpy,
				targetId: null,
				isPending: false,
			},
			cancel: {
				open: cancelOpenSpy,
				close: cancelCloseSpy,
				confirm: cancelConfirmSpy,
				confirmId: null,
				targetId: null,
				isPending: false,
			},
			removal: {
				dialog: null,
				open: openRemoveSpy,
				close: removalCloseSpy,
				cancel: removalCancelSpy,
				confirm: removeSpy,
				targetId: null,
				isPending: false,
				resolvingId: null,
			},
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
		expect(screen.getAllByRole("button", { name: "Resend" })).toHaveLength(1);

		fireEvent.click(screen.getByRole("button", { name: "Resend" }));

		await waitFor(() => {
			expect(resendSpy).toHaveBeenCalledWith("invite-1");
		});
	});

	it("shows remove action and confirms removal for accepted invitations", async () => {
		mockUseCircleInvitationListController.mockReturnValue({
			invitations,
			query: {
				isFetching: false,
				isLoading: false,
				error: null,
				refetch: vi.fn(),
			},
			resend: {
				trigger: resendSpy,
				targetId: null,
				isPending: false,
			},
			cancel: {
				open: cancelOpenSpy,
				close: cancelCloseSpy,
				confirm: cancelConfirmSpy,
				confirmId: null,
				targetId: null,
				isPending: false,
			},
			removal: {
				dialog: {
					invitation: invitations[1],
					memberId: "24",
				},
				open: openRemoveSpy,
				close: removalCloseSpy,
				cancel: removalCancelSpy,
				confirm: removeSpy,
				targetId: null,
				isPending: false,
				resolvingId: null,
			},
		});

		renderWithQueryClient(<CircleInvitationList circleId="42" />);

		const removeButton = screen.getByRole("button", {
			name: "Remove from circle",
		});
		fireEvent.click(removeButton);

		expect(openRemoveSpy).toHaveBeenCalledWith(invitations[1]);
		expect(
			screen.getByText("Remove sarah@example.com from this circle?"),
		).toBeInTheDocument();

		fireEvent.click(screen.getByRole("button", { name: "Yes, remove member" }));

		await waitFor(() => {
			expect(removeSpy).toHaveBeenCalled();
		});
	});
});
