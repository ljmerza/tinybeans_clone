import { Layout } from "@/components";
import { requireAuth, requireCircleOnboardingComplete } from "@/features/auth";
import { circleKeys, circleServices } from "@/features/circles";
import {
	ProfileCirclesSettings,
	ProfileGeneralSettingsCard,
	ProfileSettingsTabs,
} from "@/features/profile";
import { createFileRoute } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

function ProfileCirclesSettingsPage() {
	return (
		<Layout>
			<ProfileSettingsTabs
				general={<ProfileGeneralSettingsCard />}
				circles={<ProfileCirclesSettings />}
				twoFactor={null}
			/>
		</Layout>
	);
}

export const Route = createFileRoute("/profile/circles")({
	beforeLoad: async (args) => {
		await requireAuth(args);
		await requireCircleOnboardingComplete(args);
	},
	loader: async ({ context }) => {
		const { queryClient } = context;
		return queryClient.ensureQueryData({
			queryKey: circleKeys.list(),
			queryFn: async () => {
				const response = await circleServices.listMemberships();
				const payload = response.data ?? response;
				return payload?.circles ?? [];
			},
		});
	},
	pendingComponent: ProfileCirclesPending,
	errorComponent: ProfileCirclesError,
	component: ProfileCirclesSettingsPage,
});

function ProfileCirclesPending() {
	const { t } = useTranslation();
	return <Layout.Loading message={t("pages.circles.index.loading")} />;
}

function ProfileCirclesError({
	reset,
	error,
}: {
	reset?: () => void;
	error: unknown;
}) {
	const { t } = useTranslation();
	return (
		<Layout.Error
			title={t("pages.circles.index.error_title")}
			message={t("pages.circles.index.error_message")}
			actionLabel={t("pages.circles.index.retry")}
			onAction={() => {
				console.error("Failed to load circles", error);
				reset?.();
			}}
		/>
	);
}
