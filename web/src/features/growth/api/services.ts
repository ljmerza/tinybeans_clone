import { apiClient as authApi } from "@/features/auth/api/authClient";
import type {
	GrowthLog,
	GrowthMeasurement,
	GrowthMeasurementInput,
	PersonStats,
} from "../types";

const peoplePath = (personId: string) => `/keeps/people/${personId}`;

export const growthServices = {
	getStats(personId: string) {
		return authApi.get<PersonStats>(`${peoplePath(personId)}/stats/`);
	},

	getLog(personId: string) {
		return authApi.get<GrowthLog>(`${peoplePath(personId)}/growth/`);
	},

	/** Circle admins only. */
	create(personId: string, input: GrowthMeasurementInput) {
		return authApi.post<GrowthMeasurement>(
			`${peoplePath(personId)}/growth/`,
			input,
		);
	},

	/** Circle admins only; send just the fields that changed. */
	update(
		personId: string,
		measurementId: string,
		input: Partial<GrowthMeasurementInput>,
	) {
		return authApi.patch<GrowthMeasurement>(
			`${peoplePath(personId)}/growth/${measurementId}/`,
			input,
		);
	},

	/** Circle admins only. */
	remove(personId: string, measurementId: string) {
		return authApi.delete<void>(
			`${peoplePath(personId)}/growth/${measurementId}/`,
		);
	},
};
