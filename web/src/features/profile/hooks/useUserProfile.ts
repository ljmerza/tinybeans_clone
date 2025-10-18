import type { AuthUser } from "@/features/auth/types";
import type { UseQueryOptions, UseQueryResult } from "@tanstack/react-query";
import { useQuery } from "@tanstack/react-query";
import { profileKeys } from "../api/queryKeys";
import { type UserProfileResponse, profileServices } from "../api/services";

export function fetchUserProfile() {
	return profileServices.getProfile();
}

export function useUserProfileQuery(
	options?: Omit<UseQueryOptions<AuthUser>, "queryKey" | "queryFn">,
): UseQueryResult<AuthUser> {
	return useQuery({
		queryKey: profileKeys.profile(),
		queryFn: async () => {
			const response = await fetchUserProfile();
			const data = (response.data ?? response) as UserProfileResponse;
			return data.user;
		},
		...options,
	});
}
