import {
	AuthSessionProvider,
	type AuthUser,
	authServices,
	setAccessToken,
} from "@/features/auth";
import { profileServices } from "@/features/profile/api/services";
import type { ReactNode } from "react";
import { vi } from "vitest";
import type { GrowthLog, GrowthMeasurement, PersonStats } from "./types";
import type { MeasurementUnits } from "./utils/units";

/** A measurement as the API returns it, for tests. */
export function makeMeasurement(
	overrides: Partial<GrowthMeasurement> = {},
): GrowthMeasurement {
	return {
		id: "cccccccc-0000-0000-0000-000000000001",
		measured_on: "2025-06-01",
		height_cm: 61.5,
		weight_kg: 6.265,
		note: "",
		created_at: "2025-06-01T12:00:00Z",
		updated_at: "2025-06-01T12:00:00Z",
		...overrides,
	};
}

export function makeGrowthLog(overrides: Partial<GrowthLog> = {}): GrowthLog {
	return {
		can_edit: false,
		birthdate: "2025-01-15",
		measurements: [],
		...overrides,
	};
}

export function makeStats(overrides: Partial<PersonStats> = {}): PersonStats {
	return {
		birthdate: null,
		age: null,
		post_count: 0,
		photo_count: 0,
		video_count: 0,
		posts_per_month: [],
		first_post: null,
		most_liked_post: null,
		...overrides,
	};
}

/**
 * Signs a user in for the test: the session loads them with `units`, and
 * profile saves update what the session returns next. Call
 * `setAccessToken(null)` (or `vi.restoreAllMocks`) afterwards.
 */
export function mockSignedInUser(units: MeasurementUnits = "imperial") {
	let user: AuthUser = { id: 1, email: "a@b.c", measurement_units: units };
	setAccessToken("test-token");
	vi.spyOn(authServices, "getSession").mockImplementation(async () => ({
		data: { user },
	}));
	const updateProfile = vi
		.spyOn(profileServices, "updateProfile")
		.mockImplementation(async (body) => {
			user = { ...user, ...body };
			return { data: { user } };
		});
	return { updateProfile };
}

export const withSession = (children: ReactNode) => (
	<AuthSessionProvider>{children}</AuthSessionProvider>
);
