import { authKeys, useAuthSession } from "@/features/auth";
import type { AuthUser } from "@/features/auth/types";
import { useUpdateUserProfileMutation } from "@/features/profile/hooks/useUpdateUserProfileMutation";
import { useQueryClient } from "@tanstack/react-query";
import { type MeasurementUnits, toMeasurementUnits } from "../utils/units";

/**
 * The viewer's measurement units, saved on their account. Switching applies at
 * once everywhere (it patches the cached session user) and is undone if the
 * save fails.
 */
export function useMeasurementUnits() {
	const session = useAuthSession();
	const queryClient = useQueryClient();
	const updateProfile = useUpdateUserProfileMutation({
		suppressSuccessToast: true,
	});
	const units = toMeasurementUnits(session.user?.measurement_units);

	const setSessionUnits = (value: MeasurementUnits) => {
		queryClient.setQueryData<AuthUser>(authKeys.session(), (user) =>
			user ? { ...user, measurement_units: value } : user,
		);
	};

	const setUnits = async (next: MeasurementUnits) => {
		if (next === units) return;
		const previous = units;
		setSessionUnits(next);
		try {
			await updateProfile.mutateAsync({ measurement_units: next });
		} catch (error) {
			console.error("Failed to save measurement units:", error);
			setSessionUnits(previous);
		}
	};

	return { units, setUnits, isSaving: updateProfile.isPending };
}
