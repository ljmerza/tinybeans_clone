import { apiClient as authApi } from "@/features/auth/api/authClient";

import type {
	AiConnectionTest,
	AiSettings,
	AvailableAiSettings,
	UpdateAiSettingsInput,
} from "../types";

const circlePath = (circleId: number | string) => `/users/circles/${circleId}`;

/** Circle admins only; the API refuses anyone else. */
export const aiAssistServices = {
	getSettings(circleId: number | string) {
		return authApi.get<AiSettings>(`${circlePath(circleId)}/ai-settings/`);
	},

	updateSettings(circleId: number | string, input: UpdateAiSettingsInput) {
		// The client has no put helper; the API takes PUT only.
		return authApi.request<AvailableAiSettings>(
			`${circlePath(circleId)}/ai-settings/`,
			{ method: "PUT", body: JSON.stringify(input) },
		);
	},

	/** Sends one made-up caption to the operator's model; never a real post. */
	testConnection(circleId: number | string) {
		return authApi.post<AiConnectionTest>(
			`${circlePath(circleId)}/ai-settings/test/`,
		);
	},

	/** Queues a scan of the circle's new posts, like the nightly one. */
	scanNow(circleId: number | string) {
		return authApi.post<{ queued: true }>(
			`${circlePath(circleId)}/milestones/scan/`,
		);
	},
};
