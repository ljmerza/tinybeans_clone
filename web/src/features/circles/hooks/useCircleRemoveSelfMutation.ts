import { useAuthSession } from "@/features/auth";
import { useApiMessages } from "@/i18n";
import { showToast } from "@/lib/toast";
import type { ApiError, ApiResponseWithMessages } from "@/types";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { circleKeys } from "../api/queryKeys";
import { circleServices } from "../api/services";

interface RemoveSelfInput {
	circleId: number;
}

export function useCircleRemoveSelfMutation() {
	const { t } = useTranslation();
	const session = useAuthSession();
	const { showAsToast } = useApiMessages();
	const queryClient = useQueryClient();

	return useMutation<ApiResponseWithMessages, ApiError, RemoveSelfInput>({
		mutationFn: async ({ circleId }) => {
			const userId = session.user?.id;
			if (!userId) {
				throw Object.assign(
					new Error("Cannot leave a circle without a signed-in user"),
					{ status: 400, messages: [] },
				);
			}
			return circleServices.removeMember(circleId, userId);
		},
		onSuccess: (response) => {
			// Invalidate circles list to trigger a refetch
			void queryClient.invalidateQueries({
				queryKey: circleKeys.list(),
			});

			if (response?.messages?.length) {
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
