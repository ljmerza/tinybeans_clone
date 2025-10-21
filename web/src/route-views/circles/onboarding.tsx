import { Layout } from "@/components/Layout";
import { useCircleOnboardingQuery } from "@/features/circles/hooks/useCircleOnboarding";
import { useNavigate } from "@tanstack/react-router";
import { useCallback, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { CircleOnboardingContent } from "./components/CircleOnboardingContent";

export default function CircleOnboardingRoute() {
	const { t } = useTranslation();
	const navigate = useNavigate();
	const { data, isLoading, isError, refetch, isFetching } =
		useCircleOnboardingQuery();

	useEffect(() => {
		if (data && !data.needs_circle_onboarding) {
			navigate({ to: "/" });
		}
	}, [data, navigate]);

	const handleRefresh = useCallback(async () => {
		const result = await refetch();
		return result.data;
	}, [refetch]);

	const handleRetry = useCallback(() => {
		void handleRefresh();
	}, [handleRefresh]);

	if (isLoading) {
		return <Layout.Loading message={t("pages.circleOnboarding.loading")} />;
	}

	if (isError || !data) {
		return (
			<Layout.Error
				title={t("pages.circleOnboarding.errorTitle")}
				message={t("pages.circleOnboarding.errorMessage")}
				actionLabel={t("common.retry")}
				onAction={handleRetry}
			/>
		);
	}

	return (
		<Layout>
			<CircleOnboardingContent
				status={data}
				onRefresh={handleRefresh}
				isRefreshing={isFetching}
			/>
		</Layout>
	);
}
