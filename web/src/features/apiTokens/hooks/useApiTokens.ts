import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiTokenKeys } from "../api/queryKeys";
import { apiTokenServices } from "../api/services";
import type { CreateApiTokenInput } from "../types";

/** The circle's API tokens, including revoked and expired ones (circle admins only). */
export function useApiTokens(
	circleId: number | string,
	{ enabled = true }: { enabled?: boolean } = {},
) {
	return useQuery({
		queryKey: apiTokenKeys.list(circleId),
		queryFn: () => apiTokenServices.list(circleId),
		enabled,
	});
}

/**
 * Creates a token. The response holds the only copy of the plaintext, so the
 * mutation never pauses offline and is dropped from the cache as soon as
 * nothing observes it; call `reset()` once the plaintext has been shown.
 */
export function useCreateApiToken(circleId: number | string) {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: (input: CreateApiTokenInput) =>
			apiTokenServices.create(circleId, input),
		networkMode: "always",
		gcTime: 0,
		onSuccess: () => {
			void queryClient.invalidateQueries({
				queryKey: apiTokenKeys.list(circleId),
			});
		},
	});
}

/** Revokes a token at once; any admin of the circle may. */
export function useRevokeApiToken(circleId: number | string) {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: (tokenId: string) => apiTokenServices.revoke(circleId, tokenId),
		meta: {
			toast: {
				success: { key: "pages.circles.dashboard.api_tokens.revoked" },
				error: { key: "pages.circles.dashboard.api_tokens.revoke_failed" },
			},
		},
		onSettled: () => {
			void queryClient.invalidateQueries({
				queryKey: apiTokenKeys.list(circleId),
			});
		},
	});
}
