import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
	twoFaKeys,
	twoFactorServices,
	useTwoFactorSettings,
} from "@/features/twofa";

vi.mock("@/features/twofa/api/services", () => ({
	twoFactorServices: {
		getStatus: vi.fn(),
		removeMethod: vi.fn(),
		setPreferredMethod: vi.fn(),
	},
}));

vi.mock("react-i18next", async () => {
	const actual =
		await vi.importActual<typeof import("react-i18next")>("react-i18next");
	return {
		...actual,
		useTranslation: () => ({
			t: (key: string) => key,
		}),
	};
});

const mockedServices = twoFactorServices as unknown as {
	getStatus: ReturnType<typeof vi.fn>;
	removeMethod: ReturnType<typeof vi.fn>;
	setPreferredMethod: ReturnType<typeof vi.fn>;
};

function setupQueryClient(status?: unknown) {
	const queryClient = new QueryClient({
		defaultOptions: {
			queries: {
				retry: false,
			},
		},
	});

	if (status) {
		queryClient.setQueryData(twoFaKeys.status(), status);
	}

	const wrapper = ({ children }: { children: ReactNode }) => (
		<QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
	);

	return { queryClient, wrapper };
}

describe("useTwoFactorSettings", () => {
	const baseStatus = {
		is_enabled: true,
		preferred_method: "email",
		has_email: true,
		has_sms: false,
		has_totp: false,
		email_address: "user@example.com",
	} as const;

	beforeEach(() => {
		vi.clearAllMocks();
		mockedServices.getStatus.mockResolvedValue(baseStatus);
		mockedServices.removeMethod.mockResolvedValue({
			message: "removed",
			method_removed: "email",
			preferred_method_changed: false,
			twofa_disabled: false,
			status: baseStatus,
		});
		mockedServices.setPreferredMethod.mockResolvedValue({
			preferred_method: "sms",
			message: "updated",
		});
	});

	it("returns status once loaded", async () => {
		const { wrapper } = setupQueryClient();
		const { result } = renderHook(() => useTwoFactorSettings(), { wrapper });

		await waitFor(() => expect(result.current.status).toBeDefined());
		expect(result.current.status?.preferred_method).toBe("email");
		expect(result.current.removalError).toBeNull();
		expect(result.current.switchError).toBeNull();
	});

	it("handles removal request and confirmation", async () => {
		const { wrapper } = setupQueryClient();
		const { result } = renderHook(() => useTwoFactorSettings(), { wrapper });
		await waitFor(() => expect(result.current.status).toBeDefined());

		act(() => {
			result.current.requestRemoval("email");
		});
		expect(result.current.methodToRemove).toBe("email");

		await act(async () => {
			await result.current.confirmRemoval();
		});

		expect(mockedServices.removeMethod).toHaveBeenCalledWith("email");
		expect(result.current.methodToRemove).toBeNull();
		expect(result.current.removalError).toBeNull();
	});

	it("handles preferred method switch errors", async () => {
		mockedServices.setPreferredMethod.mockRejectedValueOnce(
			new Error("failed"),
		);
		const { wrapper } = setupQueryClient(baseStatus);
		const { result } = renderHook(() => useTwoFactorSettings(), { wrapper });
		await waitFor(() => expect(result.current.status).toBeDefined());

		await act(async () => {
			await result.current.setAsDefault("sms");
		});

		expect(mockedServices.setPreferredMethod).toHaveBeenCalledWith("sms");
		expect(result.current.switchError).toBeTruthy();
	});
});
