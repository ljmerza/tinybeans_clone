import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { growthKeys } from "../api/queryKeys";
import { growthServices } from "../api/services";
import type {
	GrowthLog,
	GrowthMeasurement,
	GrowthMeasurementInput,
} from "../types";

/** Oldest first, like the server sorts them. */
function byDate(a: GrowthMeasurement, b: GrowthMeasurement) {
	return (
		a.measured_on.localeCompare(b.measured_on) ||
		a.created_at.localeCompare(b.created_at)
	);
}

/** Age, post counts, posts per month and highlights for the person page. */
export function usePersonStats(personId: string) {
	return useQuery({
		queryKey: growthKeys.stats(personId),
		queryFn: () => growthServices.getStats(personId),
		staleTime: 0,
	});
}

/** A child's growth log; only fetched while `enabled` (child-kind people). */
export function useGrowthLog(personId: string, enabled = true) {
	return useQuery({
		queryKey: growthKeys.log(personId),
		queryFn: () => growthServices.getLog(personId),
		enabled,
	});
}

/** Patches the cached log with a saved measurement, in date order. */
function useStoreMeasurement(personId: string) {
	const queryClient = useQueryClient();
	return (saved: GrowthMeasurement) => {
		queryClient.setQueryData<GrowthLog>(growthKeys.log(personId), (log) =>
			log
				? {
						...log,
						measurements: [
							...log.measurements.filter((item) => item.id !== saved.id),
							saved,
						].sort(byDate),
					}
				: log,
		);
	};
}

export function useCreateMeasurement(personId: string) {
	const store = useStoreMeasurement(personId);
	return useMutation({
		mutationFn: (input: GrowthMeasurementInput) =>
			growthServices.create(personId, input),
		meta: {
			toast: { error: { key: "pages.people.growth.form.save_failed" } },
		},
		onSuccess: store,
	});
}

export function useUpdateMeasurement(personId: string) {
	const store = useStoreMeasurement(personId);
	return useMutation({
		mutationFn: ({
			measurementId,
			input,
		}: {
			measurementId: string;
			input: Partial<GrowthMeasurementInput>;
		}) => growthServices.update(personId, measurementId, input),
		meta: {
			toast: { error: { key: "pages.people.growth.form.save_failed" } },
		},
		onSuccess: store,
	});
}

export function useDeleteMeasurement(personId: string) {
	const queryClient = useQueryClient();
	return useMutation({
		mutationFn: (measurementId: string) =>
			growthServices.remove(personId, measurementId),
		meta: {
			toast: { error: { key: "pages.people.growth.delete.failed" } },
		},
		onSuccess: (_result, measurementId) => {
			queryClient.setQueryData<GrowthLog>(growthKeys.log(personId), (log) =>
				log
					? {
							...log,
							measurements: log.measurements.filter(
								(item) => item.id !== measurementId,
							),
						}
					: log,
			);
		},
	});
}
