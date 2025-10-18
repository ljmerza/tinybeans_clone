import type { AuthRequestOptions } from "@/features/auth/api/authClient";
import { apiClient as authApi } from "@/features/auth/api/authClient";
import type { AuthUser } from "@/features/auth/types";
import type { ApiResponseWithMessages } from "@/types";

export interface UserProfileResponse {
	user: AuthUser;
}

export type UpdateUserProfileRequest = Partial<AuthUser> & {
	[key: string]: unknown;
};

export const profileServices = {
	getProfile() {
		return authApi.get<ApiResponseWithMessages<UserProfileResponse>>(
			"/users/me/",
		);
	},

	updateProfile(body: UpdateUserProfileRequest, options?: AuthRequestOptions) {
		return authApi.patch<ApiResponseWithMessages<UserProfileResponse>>(
			"/users/me/",
			body,
			options,
		);
	},
};
