import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useCircleOnboardingController } from "@/features/circles";
import type { CircleOnboardingPayload } from "@/features/circles";
import {
	useCreateCircleMutation,
	useSkipCircleOnboarding,
} from "@/features/circles/hooks/useCircleOnboarding";

vi.mock("@/features/circles/hooks/useCircleOnboarding", () => ({
	useCreateCircleMutation: vi.fn(),
	useSkipCircleOnboarding: vi.fn(),
}));

vi.mock("@/i18n", () => ({
	useApiMessages: () => ({
		getGeneral: () => [],
	}),
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

const statusFixture: CircleOnboardingPayload = {
	email: "user@example.com",
	email_verified: true,
	needs_circle_onboarding: true,
	status: "email_required",
	memberships_count: 0,
	updated_at: null,
};

const navigateHomeMock = vi.fn();
const circleCreatedMock = vi.fn();

const useCreateCircleMutationMock = vi.mocked(useCreateCircleMutation);
const useSkipCircleOnboardingMock = vi.mocked(useSkipCircleOnboarding);

describe("useCircleOnboardingController", () => {
	beforeEach(() => {
		vi.clearAllMocks();
		createMutationMock.mutateAsync.mockResolvedValue(undefined);
		skipMutationMock.mutateAsync.mockResolvedValue(undefined);
		navigateHomeMock.mockReset();
		circleCreatedMock.mockReset();

		useCreateCircleMutationMock.mockReturnValue(createMutationMock);
		useSkipCircleOnboardingMock.mockReturnValue(skipMutationMock);
	});

	it("navigates home after skipping onboarding", async () => {
		const { result } = renderHook(() =>
			useCircleOnboardingController({
				status: statusFixture,
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
				status: statusFixture,
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
				status: statusFixture,
				onNavigateHome: navigateHomeMock,
			}),
		);

		await act(async () => {
			result.current.form.setFieldValue("name", "Test Circle");
			await result.current.form.handleSubmit();
		});

		expect(navigateHomeMock).toHaveBeenCalled();
	});

	it("disables submission when email is not verified", () => {
		const { result } = renderHook(() =>
			useCircleOnboardingController({
				status: { ...statusFixture, email_verified: false },
				onNavigateHome: navigateHomeMock,
			}),
		);

		expect(result.current.canSubmit).toBe(false);
	});
});
