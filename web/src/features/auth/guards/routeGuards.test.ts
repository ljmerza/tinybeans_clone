import { createTestQueryClient } from "@/lib/query/queryClient";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { authKeys } from "../api/queryKeys";
import { authServices } from "../api/services";
import { setAccessToken } from "../store/authStore";
import type { AuthUser } from "../types";
import { requireCircleOnboardingComplete } from "./routeGuards";

const user = (needs: boolean) =>
	({ id: 1, needs_circle_onboarding: needs }) as unknown as AuthUser;

function guard(queryClient = createTestQueryClient()) {
	return requireCircleOnboardingComplete({ context: { queryClient } });
}

beforeEach(() => setAccessToken("token"));

afterEach(() => {
	vi.restoreAllMocks();
	setAccessToken(null);
});

describe("requireCircleOnboardingComplete", () => {
	it("sends someone who still needs onboarding there", async () => {
		const queryClient = createTestQueryClient();
		queryClient.setQueryData(authKeys.session(), user(true));

		await expect(guard(queryClient)).rejects.toMatchObject({
			options: { to: "/circles/onboarding" },
		});
	});

	it("lets guests through", async () => {
		setAccessToken(null);

		await expect(guard()).resolves.toBeUndefined();
	});

	it("refetches an invalidated session instead of trusting it", async () => {
		// Just skipped onboarding: the cached user still says it's needed.
		const queryClient = createTestQueryClient();
		queryClient.setQueryData(authKeys.session(), user(true));
		void queryClient.invalidateQueries({ queryKey: authKeys.session() });
		vi.spyOn(authServices, "getSession").mockResolvedValue({
			data: { user: user(false) },
		} as Awaited<ReturnType<typeof authServices.getSession>>);

		await expect(guard(queryClient)).resolves.toBeUndefined();
	});
});
