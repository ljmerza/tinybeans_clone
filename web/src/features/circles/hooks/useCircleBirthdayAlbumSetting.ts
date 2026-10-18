import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { circleKeys } from "../api/queryKeys";
import { circleServices } from "../api/services";
import type { CircleChild, CircleSummary } from "../types";
import type { CircleMembersPayload } from "./useCircleMemberships";

/**
 * Turns a circle's Birthdays album on or off (circle admins only; the API
 * refuses anyone else). Updates the circle on its settings page in place.
 */
export function useCircleBirthdayAlbumSettingMutation(
	circleId: number | string,
) {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: async (enabled: boolean) => {
			const response = await circleServices.updateCircle(circleId, {
				birthday_album_enabled: enabled,
			});
			return (response.data ?? response) as { circle: CircleSummary };
		},
		onSuccess: ({ circle }) => {
			queryClient.setQueryData<CircleMembersPayload>(
				circleKeys.members(circleId),
				(current) => (current ? { ...current, circle } : current),
			);
			void queryClient.invalidateQueries({ queryKey: circleKeys.list() });
		},
		meta: {
			toast: {
				error: { key: "pages.circles.dashboard.birthdays.save_failed" },
			},
		},
	});
}

/** The circle's children with their birthdates (circle admins only). */
export function useCircleChildren(
	circleId: number | string,
	{ enabled = true }: { enabled?: boolean } = {},
) {
	return useQuery({
		queryKey: circleKeys.children(circleId),
		queryFn: async () => {
			const response = await circleServices.listChildren(circleId);
			const payload = (response.data ?? response) as {
				children?: CircleChild[];
			};
			return payload.children ?? [];
		},
		enabled,
	});
}

/**
 * Sets or clears a child's birthdate (circle admins only). The API refreshes
 * the Birthdays album in the background when it is on.
 */
export function useChildBirthdateMutation(circleId: number | string) {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: async ({
			childId,
			birthdate,
		}: {
			childId: string;
			birthdate: string | null;
		}) => {
			const response = await circleServices.updateChildBirthdate(
				childId,
				birthdate,
			);
			return (response.data ?? response) as { child: CircleChild };
		},
		onSuccess: ({ child }) => {
			queryClient.setQueryData<CircleChild[]>(
				circleKeys.children(circleId),
				(current) =>
					current?.map((item) => (item.id === child.id ? child : item)),
			);
		},
		meta: {
			toast: {
				error: {
					key: "pages.circles.dashboard.birthdays.birthdate_save_failed",
				},
			},
		},
	});
}
