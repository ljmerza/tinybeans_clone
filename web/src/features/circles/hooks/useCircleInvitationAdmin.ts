import { useApiMessages } from "@/i18n";
import { showToast } from "@/lib/toast";
import type { ApiError, ApiResponseWithMessages } from "@/types";
import {
	type UseMutationResult,
	type UseQueryResult,
	useMutation,
	useQuery,
	useQueryClient,
} from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { circleKeys } from "../api/queryKeys";
import { circleServices } from "../api/services";
import type { CircleInvitationSummary } from "../types";

interface CreateInvitationVariables {
	email: string;
	role: string;
}

function extractInvitationList(
	response: ApiResponseWithMessages<{ invitations: CircleInvitationSummary[] }>,
) {
	if ("data" in response && response.data) {
		return response.data.invitations;
	}
	return response.invitations;
}

export function useCircleInvitationsQuery(
	circleId: number | string,
): UseQueryResult<CircleInvitationSummary[]> {
	return useQuery({
		queryKey: circleKeys.invitations(circleId),
		queryFn: async () => {
			try {
				const response = await circleServices.getInvitations(circleId);
				return extractInvitationList(response);
			} catch (error) {
				const apiError = error as ApiError;
				if (apiError.status === 404) {
					return [];
				}
				throw error;
			}
		},
	});
}

export function useCreateCircleInvitation(
	circleId: number | string,
): UseMutationResult<
	ApiResponseWithMessages<{ invitation: CircleInvitationSummary }>,
	ApiError,
	CreateInvitationVariables
> {
	const queryClient = useQueryClient();
	const { showAsToast } = useApiMessages();

	return useMutation({
		mutationFn: async (variables) => {
			return circleServices.createInvitation(circleId, variables);
		},
		onSuccess: (response) => {
			const payload = (response.data ?? response) as
				| { invitation?: CircleInvitationSummary }
				| undefined;
			if (payload?.invitation) {
				queryClient.setQueryData<CircleInvitationSummary[]>(
					circleKeys.invitations(circleId),
					(previous) => {
						const list = previous ?? [];
						const filtered = list.filter(
							(invite) => invite.id !== payload.invitation?.id,
						);
						return [payload.invitation, ...filtered];
					},
				);
			}
			if (response.messages?.length) {
				showAsToast(response.messages, 202);
			}
		},
		onError: (error) => {
			showAsToast(error.messages, error.status ?? 400);
		},
	});
}

export function useResendCircleInvitation(
	circleId: number | string,
): UseMutationResult<
	ApiResponseWithMessages<{ invitation: CircleInvitationSummary }>,
	ApiError,
	string
> {
	const queryClient = useQueryClient();
	const { showAsToast } = useApiMessages();

	return useMutation({
		mutationFn: (invitationId: string) =>
			circleServices.resendInvitation(circleId, invitationId),
		onSuccess: (response) => {
			queryClient.invalidateQueries({ queryKey: circleKeys.invitations(circleId) });
			if (response.messages?.length) {
				showAsToast(response.messages, 200);
			}
		},
		onError: (error) => {
			showAsToast(error.messages, error.status ?? 400);
		},
	});
}

export function useCancelCircleInvitation(
	circleId: number | string,
): UseMutationResult<
	ApiResponseWithMessages<{ invitation: CircleInvitationSummary }>,
	ApiError,
	string
> {
	const queryClient = useQueryClient();
	const { showAsToast } = useApiMessages();

	return useMutation({
		mutationFn: (invitationId: string) =>
			circleServices.cancelInvitation(circleId, invitationId),
		onSuccess: (response, invitationId) => {
			const payload = (response.data ?? response) as
				| { invitation_id?: string }
				| undefined;
			const removedId = payload?.invitation_id ?? invitationId;
			queryClient.setQueryData<CircleInvitationSummary[]>(
				circleKeys.invitations(circleId),
				(previous) => {
					if (!previous) return [];
					return previous.filter((invitation) => invitation.id !== removedId);
				},
			);
			queryClient.invalidateQueries({
				queryKey: circleKeys.invitations(circleId),
				refetchType: "active",
			});
			if (response.messages?.length) {
				showAsToast(response.messages, 200);
			}
		},
		onError: (error) => {
			showAsToast(error.messages, error.status ?? 400);
		},
	});
}

export function useRemoveCircleMember(
	circleId: number | string,
): UseMutationResult<ApiResponseWithMessages, ApiError, number | string> {
	const queryClient = useQueryClient();
	const { showAsToast } = useApiMessages();
	const { t } = useTranslation();

	return useMutation({
		mutationFn: (userId: number | string) =>
			circleServices.removeMember(circleId, userId),
		onSuccess: (response) => {
			queryClient.invalidateQueries({ queryKey: circleKeys.members(circleId) });
			queryClient.invalidateQueries({ queryKey: circleKeys.invitations(circleId) });
			if (response.messages?.length) {
				showAsToast(response.messages, 200);
			} else {
				showToast({
					message: t("notifications.circle.member_removed"),
					level: "success",
				});
			}
		},
		onError: (error) => {
			showAsToast(error.messages, error.status ?? 400);
		},
	});
}
