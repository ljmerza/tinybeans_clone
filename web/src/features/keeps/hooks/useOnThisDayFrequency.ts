import { authKeys, useAuthSession } from "@/features/auth";
import type { AuthUser } from "@/features/auth/types";
import { useUpdateUserProfileMutation } from "@/features/profile/hooks/useUpdateUserProfileMutation";
import { useQueryClient } from "@tanstack/react-query";
import {
	type OnThisDayFrequency,
	toOnThisDayFrequency,
} from "../utils/onThisDay";

/**
 * How often the viewer sees "On this day" cards in the home feed, saved on
 * their account. Switching applies at once (it patches the cached session
 * user) and is undone if the save fails.
 */
export function useOnThisDayFrequency() {
	const session = useAuthSession();
	const queryClient = useQueryClient();
	const updateProfile = useUpdateUserProfileMutation({
		suppressSuccessToast: true,
	});
	const frequency = toOnThisDayFrequency(session.user?.on_this_day_frequency);

	const setSessionFrequency = (value: OnThisDayFrequency) => {
		queryClient.setQueryData<AuthUser>(authKeys.session(), (user) =>
			user ? { ...user, on_this_day_frequency: value } : user,
		);
	};

	const setFrequency = async (next: OnThisDayFrequency) => {
		if (next === frequency) return;
		const previous = frequency;
		setSessionFrequency(next);
		try {
			await updateProfile.mutateAsync({ on_this_day_frequency: next });
		} catch (error) {
			console.error("Failed to save On this day frequency:", error);
			setSessionFrequency(previous);
		}
	};

	return { frequency, setFrequency, isSaving: updateProfile.isPending };
}
