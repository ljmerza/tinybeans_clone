import { FormActions, FormField } from "@/components";
import { Layout } from "@/components/Layout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { CircleOnboardingPayload } from "@/features/circles";
import { useCircleOnboardingQuery } from "@/features/circles/hooks/useCircleOnboarding";
import { useCircleOnboardingController } from "@/features/circles/hooks/useCircleOnboardingController";
import { zodValidator } from "@/lib/form";
import { circleCreateSchema } from "@/lib/validations/schemas";
import { useNavigate } from "@tanstack/react-router";
import { useCallback, useEffect } from "react";
import { useTranslation } from "react-i18next";

interface CircleOnboardingContentProps {
	status: CircleOnboardingPayload;
	onRefresh: () => Promise<CircleOnboardingPayload | undefined>;
	isRefreshing: boolean;
}

function CircleOnboardingContent({
	status,
	onRefresh,
	isRefreshing,
}: CircleOnboardingContentProps) {
	const { t } = useTranslation();
	const navigate = useNavigate();
	const {
		form,
		canSubmit,
		generalError,
		resendDisabled,
		calloutDescription,
		createCirclePending,
		skipPending,
		resendPending,
		handleResend,
		handleRefreshClick,
		handleSkip,
	} = useCircleOnboardingController({
		status,
		onRefresh,
		onNavigateHome: () => navigate({ to: "/" }),
	});

	return (
		<div className="mx-auto flex max-w-xl flex-col gap-6">
			<header className="space-y-2">
				<p className="text-sm font-medium text-muted-foreground">
					{t("pages.circleOnboarding.step", { current: 1, total: 2 })}
				</p>
				<h1 className="heading-2">{t("pages.circleOnboarding.title")}</h1>
				<p className="text-muted-foreground">
					{t("pages.circleOnboarding.description")}
				</p>
			</header>

			{!status.email_verified ? (
				<section className="space-y-3 rounded-lg border border-border bg-muted/40 p-4">
					<h2 className="text-base font-semibold">
						{t("pages.circleOnboarding.verifyTitle")}
					</h2>
					<p className="text-sm text-muted-foreground">{calloutDescription}</p>
					<div className="flex flex-wrap gap-2">
						<Button onClick={handleResend} disabled={resendDisabled}>
							{resendPending
								? t("pages.circleOnboarding.resending")
								: t("pages.circleOnboarding.resend")}
						</Button>
						<Button
							variant="outline"
							onClick={handleRefreshClick}
							disabled={isRefreshing}
						>
							{isRefreshing
								? t("pages.circleOnboarding.refreshing")
								: t("pages.circleOnboarding.refresh")}
						</Button>
					</div>
				</section>
			) : null}

			<form
				onSubmit={(event) => {
					event.preventDefault();
					event.stopPropagation();
					form.handleSubmit();
				}}
				className="space-y-4"
			>
				<form.Field
					name="name"
					validators={{ onBlur: zodValidator(circleCreateSchema.shape.name) }}
				>
					{(field) => (
						<FormField
							field={field}
							label={t("pages.circleOnboarding.circleNameLabel")}
						>
							{({ id, field: fieldApi }) => (
								<Input
									id={id}
									value={fieldApi.state.value}
									onChange={(event) =>
										fieldApi.handleChange(event.target.value)
									}
									onBlur={fieldApi.handleBlur}
									autoComplete="organization"
									required
									placeholder={t(
										"pages.circleOnboarding.circleNamePlaceholder",
									)}
									disabled={!canSubmit || createCircleMutation.isPending}
								/>
							)}
						</FormField>
					)}
				</form.Field>

				<FormActions
					messages={
						generalError
							? [
									{
										id: "circle-onboarding-error",
										variant: "error" as const,
										content: generalError,
									},
								]
							: undefined
					}
				>
					<Button
						type="submit"
						className="w-full"
						isLoading={createCirclePending}
						disabled={!canSubmit}
					>
						{createCirclePending
							? t("pages.circleOnboarding.creating")
							: t("pages.circleOnboarding.createButton")}
					</Button>
				</FormActions>
			</form>

			<Button
				variant="ghost"
				className="self-start text-muted-foreground hover:text-foreground"
				onClick={() => void handleSkip()}
				isLoading={skipPending}
			>
				{skipPending
					? t("pages.circleOnboarding.skipping")
					: t("pages.circleOnboarding.skip")}
			</Button>
		</div>
	);
}

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
