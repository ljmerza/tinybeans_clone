import { authApi, userKeys } from "@/features/auth";
import type { AuthUser } from "@/features/auth";
import type { ApiResponseWithMessages } from "@/types";
import { useQuery } from "@tanstack/react-query";

interface UserProfileResponse {
	user: AuthUser;
}

export function fetchUserProfile() {
	return authApi.get<ApiResponseWithMessages<UserProfileResponse>>(
		"/users/me/",
	);
}

export function useUserProfileQuery() {
	return useQuery({
		queryKey: userKeys.profile(),
		queryFn: async () => {
			const response = await fetchUserProfile();
			const data = response.data ?? response;
			return data.user;
		},
	});
}
