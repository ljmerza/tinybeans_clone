import { useApiMessages } from "@/i18n";
import type { ApiError } from "@/types";
import { useForm } from "@tanstack/react-form";
import { useCallback, useState } from "react";
import { useTranslation } from "react-i18next";

import type { CircleOnboardingPayload } from "../types";
import {
	useCreateCircleMutation,
	useSkipCircleOnboarding,
} from "./useCircleOnboarding";

interface CircleOnboardingControllerOptions {
	status: CircleOnboardingPayload;
	onNavigateHome: () => void;
	onCircleCreated?: (circleId: number) => void;
}

export function useCircleOnboardingController({
	status,
	onNavigateHome,
	onCircleCreated,
}: CircleOnboardingControllerOptions) {
	const { t } = useTranslation();
	const { getGeneral } = useApiMessages();

	const createCircleMutation = useCreateCircleMutation();
	const skipMutation = useSkipCircleOnboarding();

	const [generalError, setGeneralError] = useState<string | null>(null);
	const canSubmit = status.email_verified ?? true;

	const form = useForm({
		defaultValues: { name: "" },
		onSubmit: async ({ value }) => {
			if (!canSubmit) return;

			setGeneralError(null);

			try {
				const result = await createCircleMutation.mutateAsync({ name: value.name.trim() });
				const circleId = result.data?.circle?.id;
				
				if (circleId && onCircleCreated) {
					onCircleCreated(circleId);
				} else {
					onNavigateHome();
				}
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


	return {
		form,
		canSubmit,
		generalError,
		createCirclePending: createCircleMutation.isPending,
		skipPending: skipMutation.isPending,
		handleSkip,
	};
}
