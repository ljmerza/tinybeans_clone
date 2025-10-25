import { Layout } from "@/components/Layout";
import { useCircleOnboardingQuery } from "@/features/circles/hooks/useCircleOnboarding";
import { useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { CircleOnboardingContent } from "./components/CircleOnboardingContent";

export default function CircleOnboardingRoute() {
	const { t } = useTranslation();
	const navigate = useNavigate();
	const { data, isLoading, isError } = useCircleOnboardingQuery();

	useEffect(() => {
		if (data && !data.needs_circle_onboarding) {
			navigate({ to: "/" });
		}
	}, [data, navigate]);

	if (isLoading) {
		return <Layout.Loading message={t("pages.circleOnboarding.loading")} />;
	}

	if (isError || !data) {
		return (
			<Layout.Error
				title={t("pages.circleOnboarding.errorTitle")}
				message={t("pages.circleOnboarding.errorMessage")}
				actionLabel={t("common.retry")}
			/>
		);
	}

	return (
		<Layout>
			<CircleOnboardingContent status={data} />
		</Layout>
	);
}
