import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { NavigateOptions } from "../useInvitationAcceptance";
import { useInvitationAcceptance } from "../useInvitationAcceptance";

const mockUseAuthSession = vi.fn();
const mockUseStartOnboarding = vi.fn();
const mockUseFinalizeInvitation = vi.fn();
const mockUseRespondInvitation = vi.fn();
const mockLoadInvitation = vi.fn();
const mockSubscribeInvitationStorage = vi.fn();
const mockMarkInvitationRequest = vi.fn();
const mockClearInvitationRequest = vi.fn();
const mockHasActiveInvitationRequest = vi.fn();

vi.mock("@/features/auth", () => ({
	useAuthSession: () => mockUseAuthSession(),
}));

vi.mock("../useCircleInvitationOnboarding", () => ({
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
	markInvitationRequest: (...args: unknown[]) =>
		mockMarkInvitationRequest(...args),
	clearInvitationRequest: (...args: unknown[]) =>
		mockClearInvitationRequest(...args),
	hasActiveInvitationRequest: (...args: unknown[]) =>
		mockHasActiveInvitationRequest(...args),
}));

vi.mock("@/features/circles/utils/inviteAnalytics", () => ({
	rememberInviteRedirect: vi.fn(),
}));

vi.mock("react-i18next", async () => {
	const actual =
		await vi.importActual<typeof import("react-i18next")>("react-i18next");
	return {
		...actual,
		useTranslation: () => ({
			t: (key: string, params?: Record<string, unknown>) => {
				if (params?.circle) {
					return `Join ${params.circle as string}`;
				}
				return key;
			},
		}),
	};
});

describe("useInvitationAcceptance", () => {
	const navigateMock = vi.fn((options: NavigateOptions) =>
		Promise.resolve(options),
	);
	const baseParams = {
		token: "abc",
		currentPath: "/invitations/accept?token=abc",
		navigate: navigateMock,
	};

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
			mutateAsync: vi.fn(),
			isPending: false,
		});
		mockUseFinalizeInvitation.mockReturnValue({
			mutate: vi.fn(),
			mutateAsync: vi.fn(),
			isPending: false,
		});
		mockUseRespondInvitation.mockReturnValue({
			mutate: vi.fn(),
			mutateAsync: vi.fn(),
			isPending: false,
		});
		mockLoadInvitation.mockReturnValue(null);
		mockSubscribeInvitationStorage.mockReturnValue(() => undefined);
		mockMarkInvitationRequest.mockImplementation(() => undefined);
		mockClearInvitationRequest.mockImplementation(() => undefined);
		mockHasActiveInvitationRequest.mockReturnValue(false);
	});

	it("returns invalid state when no token or stored invitation", () => {
		const { result } = renderHook(() =>
			useInvitationAcceptance({
				...baseParams,
				token: undefined,
			}),
		);

		expect(result.current.viewState).toBe("invalid");
	});

	it("finalizes invitation automatically when authenticated", async () => {
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

		const finalizeSpy = vi.fn(
			(
				_: string,
				options?: {
					onSuccess?: () => void;
					onError?: (error: unknown) => void;
				},
			) => {
				options?.onSuccess?.();
			},
		);

		mockUseFinalizeInvitation.mockReturnValue({
			mutate: finalizeSpy,
			mutateAsync: vi.fn(),
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

		const { result } = renderHook(() => useInvitationAcceptance(baseParams));

		await waitFor(() =>
			expect(finalizeSpy).toHaveBeenCalledWith(
				"stored-token",
				expect.objectContaining({ onSuccess: expect.any(Function) }),
			),
		);

		expect(result.current.viewState).toBe("accepted");
		await waitFor(() => expect(navigateMock).toHaveBeenCalledWith({ to: "/" }));
	});

	it("redirects authenticated flow when accept clicked", async () => {
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

		const finalizeSpy = vi.fn();
		mockUseFinalizeInvitation.mockReturnValue({
			mutate: finalizeSpy,
			mutateAsync: vi.fn(),
			isPending: false,
		});

		const { result } = renderHook(() => useInvitationAcceptance(baseParams));

		await act(async () => {
			result.current.handleAccept();
		});

		expect(finalizeSpy).not.toHaveBeenCalled();
		expect(navigateMock).toHaveBeenCalledWith({
			to: "/login",
			search: expect.objectContaining({
				redirect: "/invitations/accept?token=abc&onboarding=stored-token",
			}),
		});
	});
});
