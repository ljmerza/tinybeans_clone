import { useAuthSession } from "@/features/auth";
import { useApiMessages } from "@/i18n";
import { showToast } from "@/lib/toast";
import type { ApiError, ApiResponseWithMessages } from "@/types";
import { useMutation } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { circleServices } from "../api/services";

interface RemoveSelfInput {
	circleId: number;
}

export function useCircleRemoveSelfMutation() {
	const { t } = useTranslation();
	const session = useAuthSession();
	const { showAsToast } = useApiMessages();

	return useMutation<ApiResponseWithMessages, ApiError, RemoveSelfInput>({
		mutationFn: async ({ circleId }) => {
			const userId = session.user?.id;
			if (!userId) {
				throw {
					status: 400,
					messages: [],
				} satisfies ApiError;
			}
			return circleServices.removeMember(circleId, userId);
		},
		onSuccess: (response) => {
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
