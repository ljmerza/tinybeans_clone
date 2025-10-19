import "@/i18n/config";

import { renderWithQueryClient } from "@/test-utils";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CircleInvitationList } from "./CircleInvitationList";

const mockUseCircleInvitationsQuery = vi.fn();
const mockUseResendCircleInvitation = vi.fn();
const mockUseCancelCircleInvitation = vi.fn();
const mockUseRemoveCircleMember = vi.fn();
const mockUseCircleMembers = vi.fn();

vi.mock("../hooks/useCircleInvitationAdmin", () => ({
	useCircleInvitationsQuery: (...args: unknown[]) =>
		mockUseCircleInvitationsQuery(...args),
	useResendCircleInvitation: (...args: unknown[]) =>
		mockUseResendCircleInvitation(...args),
	useCancelCircleInvitation: (...args: unknown[]) =>
		mockUseCancelCircleInvitation(...args),
	useRemoveCircleMember: (...args: unknown[]) =>
		mockUseRemoveCircleMember(...args),
}));

vi.mock("../hooks/useCircleMemberships", () => ({
	useCircleMembers: (...args: unknown[]) => mockUseCircleMembers(...args),
}));

describe("CircleInvitationList", () => {
	const resendSpy = vi.fn().mockResolvedValue({});
	const cancelSpy = vi.fn().mockResolvedValue({});
	const removeSpy = vi.fn().mockResolvedValue({});

	beforeEach(() => {
		resendSpy.mockClear();
		cancelSpy.mockClear();
		removeSpy.mockClear();
		mockUseCircleMembers.mockClear();
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
					invited_user: {
						id: 24,
						username: "sarah",
						first_name: "Sarah",
						last_name: "Doe",
					},
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

		mockUseRemoveCircleMember.mockReturnValue({
			mutateAsync: removeSpy,
			isPending: false,
		});

		mockUseCircleMembers.mockReturnValue({
			data: {
				circle: {
					id: 42,
					name: "The Circle",
					slug: "circle",
					member_count: 2,
				},
				members: [
					{
						membership_id: 101,
						user: {
							id: 24,
							username: "sarah",
							email: "sarah@example.com",
							role: "member",
							email_verified: true,
							date_joined: "2025-02-10T12:05:00Z",
							language: "en",
							circle_onboarding_status: null,
							circle_onboarding_updated_at: null,
							needs_circle_onboarding: false,
						},
						role: "member",
						created_at: "2025-02-10T12:05:00Z",
					},
				],
			},
			isLoading: false,
			isFetching: false,
			error: null,
			refetch: vi.fn().mockResolvedValue({
				data: {
					circle: {
						id: 42,
						name: "The Circle",
						slug: "circle",
						member_count: 2,
					},
					members: [
						{
							membership_id: 101,
							user: {
								id: 24,
								username: "sarah",
								email: "sarah@example.com",
								role: "member",
								email_verified: true,
								date_joined: "2025-02-10T12:05:00Z",
								language: "en",
								circle_onboarding_status: null,
								circle_onboarding_updated_at: null,
								needs_circle_onboarding: false,
							},
							role: "member",
							created_at: "2025-02-10T12:05:00Z",
						},
					],
				},
			}),
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
		renderWithQueryClient(<CircleInvitationList circleId="42" />);

		const removeButton = screen.getByRole("button", { name: "Remove from circle" });
		fireEvent.click(removeButton);

		await waitFor(() =>
			expect(
				screen.getByText("Remove sarah@example.com from this circle?"),
			).toBeInTheDocument(),
		);

		fireEvent.click(screen.getByRole("button", { name: "Yes, remove member" }));

		await waitFor(() => {
			expect(removeSpy).toHaveBeenCalledWith("24");
		});
	});
});
