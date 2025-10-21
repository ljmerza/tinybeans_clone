import { useResendVerificationMutation } from "@/features/auth";
import { useApiMessages } from "@/i18n";
import { showToast } from "@/lib/toast";
import type { ApiError } from "@/types";
import { useForm } from "@tanstack/react-form";
import { useCallback, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import type { CircleOnboardingPayload } from "../types";
import {
	useCreateCircleMutation,
	useSkipCircleOnboarding,
} from "./useCircleOnboarding";

interface CircleOnboardingControllerOptions {
	status: CircleOnboardingPayload;
	onRefresh: () => Promise<CircleOnboardingPayload | undefined>;
	onNavigateHome: () => void;
}

export function useCircleOnboardingController({
	status,
	onRefresh,
	onNavigateHome,
}: CircleOnboardingControllerOptions) {
	const { t } = useTranslation();
	const { getGeneral } = useApiMessages();

	const createCircleMutation = useCreateCircleMutation();
	const skipMutation = useSkipCircleOnboarding();
	const resendMutation = useResendVerificationMutation();

	const [generalError, setGeneralError] = useState<string | null>(null);
	const canSubmit = status.email_verified;

	const form = useForm({
		defaultValues: { name: "" },
		onSubmit: async ({ value }) => {
			if (!canSubmit) return;

			setGeneralError(null);

			try {
				await createCircleMutation.mutateAsync({ name: value.name.trim() });
				onNavigateHome();
			} catch (error) {
				const apiError = error as ApiError;
				const messages = getGeneral(apiError.messages);
				if (messages.length > 0) {
					setGeneralError(messages.join("\n"));
					return;
				}

				const fallback = apiError.message ?? t("errors.server_error");
				setGeneralError(fallback);
				console.error("Circle creation error:", error);
			}
		},
	});

	const handleSkip = useCallback(async () => {
		try {
			await skipMutation.mutateAsync();
			onNavigateHome();
		} catch (error) {
			console.error("Skip onboarding failed:", error);
		}
	}, [onNavigateHome, skipMutation]);

	const resendDisabled = !status.email || resendMutation.isPending;

	const calloutDescription = useMemo(
		() =>
			t("pages.circleOnboarding.verifyDescription", {
				email: status.email,
			}),
		[status.email, t],
	);

	const refreshAndNotify = useCallback(async () => {
		try {
			const refreshed = await onRefresh();
			if (refreshed && !refreshed.email_verified) {
				showToast({
					message: t("pages.circleOnboarding.refreshFailed"),
					level: "warning",
					id: "circle-onboarding-refresh",
				});
				return;
			}

			if (!refreshed && !status.email_verified) {
				showToast({
					message: t("pages.circleOnboarding.refreshFailed"),
					level: "warning",
					id: "circle-onboarding-refresh",
				});
			}
		} catch (error) {
			console.error("Circle onboarding refresh failed:", error);
		}
	}, [onRefresh, status.email_verified, t]);

	const handleRefreshClick = useCallback(() => {
		void refreshAndNotify();
	}, [refreshAndNotify]);

	const handleResend = useCallback(() => {
		if (!status.email || resendMutation.isPending) return;
		resendMutation.mutate(status.email);
	}, [resendMutation, status.email]);

	return {
		form,
		canSubmit,
		generalError,
		resendDisabled,
		calloutDescription,
		createCirclePending: createCircleMutation.isPending,
		skipPending: skipMutation.isPending,
		resendPending: resendMutation.isPending,
		handleResend,
		handleRefreshClick,
		handleSkip,
	};
}
