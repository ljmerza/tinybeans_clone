import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { CircleInvitationSummary, CircleMemberSummary } from "../../types";
import { useCircleInvitationListController } from "../useCircleInvitationListController";

const mockUseCircleInvitationsQuery = vi.fn();
const mockUseResendCircleInvitation = vi.fn();
const mockUseCancelCircleInvitation = vi.fn();
const mockUseRemoveCircleMember = vi.fn();
const mockUseCircleMembers = vi.fn();
const showToastMock = vi.fn();

vi.mock("../useCircleInvitationAdmin", () => ({
	useCircleInvitationsQuery: (...args: unknown[]) =>
		mockUseCircleInvitationsQuery(...args),
	useResendCircleInvitation: (...args: unknown[]) =>
		mockUseResendCircleInvitation(...args),
	useCancelCircleInvitation: (...args: unknown[]) =>
		mockUseCancelCircleInvitation(...args),
	useRemoveCircleMember: (...args: unknown[]) =>
		mockUseRemoveCircleMember(...args),
}));

vi.mock("../useCircleMemberships", () => ({
	useCircleMembers: (...args: unknown[]) => mockUseCircleMembers(...args),
}));

vi.mock("@/lib/toast", () => ({
	showToast: (...args: unknown[]) => showToastMock(...args),
}));

vi.mock("react-i18next", async () => {
	const actual =
		await vi.importActual<typeof import("react-i18next")>("react-i18next");
	return {
		...actual,
		useTranslation: () => ({
			t: (key: string) => key,
			i18n: { language: "en" },
		}),
	};
});

const baseInvitations: CircleInvitationSummary[] = [
	{
		id: "invite-old",
		email: "old@example.com",
		existing_user: false,
		role: "member",
		status: "pending",
		created_at: "2024-01-01T00:00:00Z",
		responded_at: null,
		reminder_sent_at: null,
		invited_user: null,
	},
	{
		id: "invite-new",
		email: "new@example.com",
		existing_user: true,
		role: "member",
		status: "accepted",
		created_at: "2024-02-01T00:00:00Z",
		responded_at: "2024-02-02T00:00:00Z",
		reminder_sent_at: null,
		invited_user: {
			id: 42,
			username: "newuser",
			first_name: "New",
			last_name: "Member",
		},
	},
];

const memberFixture: CircleMemberSummary = {
	membership_id: 101,
	user: {
		id: 42,
		username: "newuser",
		email: "new@example.com",
		role: "member",
		email_verified: true,
		date_joined: "2024-02-02T00:00:00Z",
		language: "en",
		circle_onboarding_status: null,
		circle_onboarding_updated_at: null,
		needs_circle_onboarding: false,
	},
	role: "member",
	created_at: "2024-02-02T00:00:00Z",
};

describe("useCircleInvitationListController", () => {
	beforeEach(() => {
		mockUseCircleInvitationsQuery.mockReset();
		mockUseResendCircleInvitation.mockReset();
		mockUseCancelCircleInvitation.mockReset();
		mockUseRemoveCircleMember.mockReset();
		mockUseCircleMembers.mockReset();
		showToastMock.mockReset();

		mockUseCircleInvitationsQuery.mockReturnValue({
			data: baseInvitations,
			isFetching: false,
			isLoading: false,
			error: null,
			refetch: vi.fn(),
		});

		mockUseResendCircleInvitation.mockReturnValue({
			mutateAsync: vi.fn().mockResolvedValue(undefined),
			isPending: false,
		});

		mockUseCancelCircleInvitation.mockReturnValue({
			mutateAsync: vi.fn().mockResolvedValue(undefined),
			isPending: false,
		});

		mockUseRemoveCircleMember.mockReturnValue({
			mutateAsync: vi.fn().mockResolvedValue(undefined),
			isPending: false,
		});

		mockUseCircleMembers.mockReturnValue({
			data: { members: [memberFixture] },
			refetch: vi
				.fn()
				.mockResolvedValue({ data: { members: [memberFixture] } }),
			isLoading: false,
			isFetching: false,
			error: null,
		});
	});

	it("sorts invitations by newest first", () => {
		const { result } = renderHook(() =>
			useCircleInvitationListController("circle-1"),
		);

		expect(result.current.invitations).toHaveLength(2);
		expect(result.current.invitations[0].id).toBe("invite-new");
		expect(result.current.invitations[1].id).toBe("invite-old");
	});

	it("tracks resend target while mutation is in-flight", async () => {
		let resolveMutation: (() => void) | null = null;
		const mutateAsync = vi.fn(
			() =>
				new Promise<void>((resolve) => {
					resolveMutation = resolve;
				}),
		);

		mockUseResendCircleInvitation.mockReturnValue({
			mutateAsync,
			isPending: false,
		});

		const { result } = renderHook(() =>
			useCircleInvitationListController("circle-1"),
		);

		await act(async () => {
			const triggerPromise = result.current.resend.trigger("invite-new");
			expect(result.current.resend.targetId).toBe("invite-new");
			resolveMutation?.();
			await triggerPromise;
		});

		expect(mutateAsync).toHaveBeenCalledWith("invite-new");
		expect(result.current.resend.targetId).toBeNull();
	});

	it("resolves member id via refetch when not cached", async () => {
		const refetch = vi.fn().mockResolvedValue({
			data: { members: [memberFixture] },
		});
		const removeMutation = vi.fn().mockResolvedValue(undefined);

		mockUseCircleMembers.mockReturnValue({
			data: { members: [] },
			refetch,
			isLoading: false,
			isFetching: false,
			error: null,
		});

		mockUseRemoveCircleMember.mockReturnValue({
			mutateAsync: removeMutation,
			isPending: false,
		});

		const { result } = renderHook(() =>
			useCircleInvitationListController("circle-1"),
		);

		await act(async () => {
			result.current.removal.open(baseInvitations[1]);
		});

		await waitFor(() =>
			expect(result.current.removal.dialog?.memberId).toBe("42"),
		);

		await act(async () => {
			await result.current.removal.confirm();
		});

		expect(refetch).toHaveBeenCalled();
		expect(removeMutation).toHaveBeenCalledWith("42");
		expect(result.current.removal.dialog).toBeNull();
		expect(showToastMock).not.toHaveBeenCalled();
	});
});
