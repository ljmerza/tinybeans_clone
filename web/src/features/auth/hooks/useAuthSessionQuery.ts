import type { HttpError } from "@/lib/httpClient";
import {
	type UseQueryOptions,
	type UseQueryResult,
	useQuery,
} from "@tanstack/react-query";
import { useStore } from "@tanstack/react-store";
import { authKeys } from "../api/queryKeys";
import { authServices } from "../api/services";
import { authStore } from "../store/authStore";
import type { AuthUser, MeResponse } from "../types";

export interface AuthSessionQueryOptions
	extends Omit<
		UseQueryOptions<AuthUser, HttpError, AuthUser>,
		"queryKey" | "queryFn"
	> {}

export function useAuthSessionQuery(
	options: AuthSessionQueryOptions = {},
): UseQueryResult<AuthUser, HttpError> {
	const { accessToken } = useStore(authStore);

	return useQuery<AuthUser, HttpError>({
		queryKey: authKeys.session(),
		queryFn: async () => {
			const response = await authServices.getSession();
			const data = (response.data ?? response) as MeResponse;
			return data.user;
		},
		// Only run if we explicitly have an access token and not in a passive guest hover scenario.
		enabled: options.enabled ?? Boolean(accessToken),
		retry: options.retry ?? false,
		staleTime: options.staleTime ?? 1000 * 60,
		...options,
	});
}
