import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useResendVerificationMutation } from "@/features/auth";
import { useCircleOnboardingController } from "@/features/circles";
import type { CircleOnboardingPayload } from "@/features/circles";
import {
	useCreateCircleMutation,
	useSkipCircleOnboarding,
} from "@/features/circles/hooks/useCircleOnboarding";
import { showToast } from "@/lib/toast";

vi.mock("@/features/auth", () => ({
	useResendVerificationMutation: vi.fn(),
}));

vi.mock("@/features/circles/hooks/useCircleOnboarding", () => ({
	useCreateCircleMutation: vi.fn(),
	useSkipCircleOnboarding: vi.fn(),
}));

vi.mock("@/i18n", () => ({
	useApiMessages: () => ({
		getGeneral: () => [],
	}),
}));

vi.mock("@/lib/toast", () => ({
	showToast: vi.fn(),
}));

vi.mock("react-i18next", async () => {
	const actual =
		await vi.importActual<typeof import("react-i18next")>("react-i18next");
	return {
		...actual,
		useTranslation: () => ({
			t: (key: string, params?: Record<string, unknown>) => {
				if (params?.email) {
					return `${key}:${params.email as string}`;
				}
				return key;
			},
		}),
	};
});

const createMutationMock = { mutateAsync: vi.fn(), isPending: false };
const skipMutationMock = { mutateAsync: vi.fn(), isPending: false };
const resendMutationMock = { mutate: vi.fn(), isPending: false };

const statusFixture: CircleOnboardingPayload = {
	email: "user@example.com",
	email_verified: false,
	needs_circle_onboarding: true,
	status: "email_required",
	memberships_count: 0,
	updated_at: null,
};

const refreshMock = vi.fn();
const navigateHomeMock = vi.fn();
const circleCreatedMock = vi.fn();

const useCreateCircleMutationMock = vi.mocked(useCreateCircleMutation);
const useSkipCircleOnboardingMock = vi.mocked(useSkipCircleOnboarding);
const useResendVerificationMutationMock = vi.mocked(
	useResendVerificationMutation,
);

describe("useCircleOnboardingController", () => {
	beforeEach(() => {
		vi.clearAllMocks();
		createMutationMock.mutateAsync.mockResolvedValue(undefined);
		skipMutationMock.mutateAsync.mockResolvedValue(undefined);
		resendMutationMock.mutate.mockReturnValue(undefined);
		refreshMock.mockResolvedValue(undefined);
		navigateHomeMock.mockReset();
		circleCreatedMock.mockReset();

		useCreateCircleMutationMock.mockReturnValue(createMutationMock);
		useSkipCircleOnboardingMock.mockReturnValue(skipMutationMock);
		useResendVerificationMutationMock.mockReturnValue(resendMutationMock);
	});

	it("provides callout description and handles resend", () => {
		const { result } = renderHook(() =>
			useCircleOnboardingController({
				status: statusFixture,
				onRefresh: refreshMock,
				onNavigateHome: navigateHomeMock,
			}),
		);

		expect(result.current.calloutDescription).toContain(
			statusFixture.email ?? "",
		);

		act(() => {
			result.current.handleResend();
		});

		expect(resendMutationMock.mutate).toHaveBeenCalledWith("user@example.com");
	});

	it("refreshes status and surfaces warning toast when still unverified", async () => {
		refreshMock.mockResolvedValue({
			...statusFixture,
			email_verified: false,
		});

		const { result } = renderHook(() =>
			useCircleOnboardingController({
				status: statusFixture,
				onRefresh: refreshMock,
				onNavigateHome: navigateHomeMock,
			}),
		);

		await act(async () => {
			result.current.handleRefreshClick();
		});

		expect(refreshMock).toHaveBeenCalled();
		expect(showToast).toHaveBeenCalled();
	});

	it("navigates home after skipping onboarding", async () => {
		const { result } = renderHook(() =>
			useCircleOnboardingController({
				status: { ...statusFixture, email_verified: true },
				onRefresh: refreshMock,
				onNavigateHome: navigateHomeMock,
			}),
		);

		await act(async () => {
			await result.current.handleSkip();
		});

		expect(skipMutationMock.mutateAsync).toHaveBeenCalled();
		expect(navigateHomeMock).toHaveBeenCalled();
	});

	it("calls onCircleCreated with circle ID when circle is created successfully", async () => {
		const mockCircleId = 123;
		createMutationMock.mutateAsync.mockResolvedValue({
			data: {
				circle: {
					id: mockCircleId,
					name: "Test Circle",
					slug: "test-circle",
					member_count: 1,
				},
			},
			messages: [],
		});

		const { result } = renderHook(() =>
			useCircleOnboardingController({
				status: { ...statusFixture, email_verified: true },
				onRefresh: refreshMock,
				onNavigateHome: navigateHomeMock,
				onCircleCreated: circleCreatedMock,
			}),
		);

		await act(async () => {
			result.current.form.setFieldValue("name", "Test Circle");
			await result.current.form.handleSubmit();
		});

		expect(createMutationMock.mutateAsync).toHaveBeenCalledWith({
			name: "Test Circle",
		});
		expect(circleCreatedMock).toHaveBeenCalledWith(mockCircleId);
		expect(navigateHomeMock).not.toHaveBeenCalled();
	});

	it("navigates home when circle is created but onCircleCreated is not provided", async () => {
		createMutationMock.mutateAsync.mockResolvedValue({
			data: {
				circle: {
					id: 123,
					name: "Test Circle",
					slug: "test-circle",
					member_count: 1,
				},
			},
			messages: [],
		});

		const { result } = renderHook(() =>
			useCircleOnboardingController({
				status: { ...statusFixture, email_verified: true },
				onRefresh: refreshMock,
				onNavigateHome: navigateHomeMock,
			}),
		);

		await act(async () => {
			result.current.form.setFieldValue("name", "Test Circle");
			await result.current.form.handleSubmit();
		});

		expect(navigateHomeMock).toHaveBeenCalled();
	});
});
