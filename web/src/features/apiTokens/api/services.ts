import { apiClient as authApi } from "@/features/auth/api/authClient";

import type {
	ApiTokenList,
	CreateApiTokenInput,
	CreatedApiToken,
} from "../types";

const tokensPath = (circleId: number | string) =>
	`/users/circles/${circleId}/api-tokens/`;

/** Circle admins only; the API refuses anyone else. */
export const apiTokenServices = {
	list(circleId: number | string) {
		return authApi.get<ApiTokenList>(tokensPath(circleId));
	},

	/** Needs the emailed re-authentication code. */
	create(circleId: number | string, input: CreateApiTokenInput) {
		return authApi.post<CreatedApiToken>(tokensPath(circleId), input);
	},

	/** Idempotent. */
	revoke(circleId: number | string, tokenId: string) {
		return authApi.delete<unknown>(`${tokensPath(circleId)}${tokenId}/`);
	},
};
