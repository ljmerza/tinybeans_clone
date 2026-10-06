import { useQuery } from "@tanstack/react-query";
import { getOAuthProviders } from "./client";

/**
 * Which sign-in providers the server is configured for. The Google and Apple
 * buttons stay hidden until this reports them as configured.
 */
export function useOAuthProviders() {
	return useQuery({
		queryKey: ["auth", "oauth-providers"],
		queryFn: getOAuthProviders,
		staleTime: 1000 * 60 * 30,
		retry: false,
	});
}
