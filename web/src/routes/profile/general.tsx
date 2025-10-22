import { Layout } from "@/components";
import { requireAuth, requireCircleOnboardingComplete } from "@/features/auth";
import {
	ProfileGeneralSettingsCard,
	ProfileSettingsTabs,
	profileKeys,
	profileServices,
} from "@/features/profile";
import type { QueryClient } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

function ProfileGeneralSettingsPage() {
	return (
		<Layout>
			<ProfileSettingsTabs
				general={<ProfileGeneralSettingsCard />}
				twoFactor={null}
			/>
		</Layout>
	);
}

export const Route = createFileRoute("/profile/general")({
	beforeLoad: async (args) => {
		await requireAuth(args);
		await requireCircleOnboardingComplete(args);
	},
	loader: async ({ context }) => {
		const { queryClient } = context as { queryClient: QueryClient };
		return queryClient.ensureQueryData({
			queryKey: profileKeys.profile(),
			queryFn: async () => {
				const response = await profileServices.getProfile();
				const payload = response.data ?? response;
				return payload.user;
			},
		});
	},
	pendingComponent: ProfileGeneralPending,
	errorComponent: ProfileGeneralError,
	component: ProfileGeneralSettingsPage,
});

function ProfileGeneralPending() {
	const { t } = useTranslation();

	return (
		<Layout.Loading
			message={t("profile.general.loading_title")}
			description={t("profile.general.loading_description")}
		/>
	);
}

function ProfileGeneralError({
	error,
	reset,
}: {
	error: unknown;
	reset?: () => void;
}) {
	const { t } = useTranslation();

	return (
		<Layout.Error
			title={t("profile.general.error_title")}
			description={t("profile.general.error_description")}
			actionLabel={t("common.retry")}
			onAction={() => {
				console.error("Failed to load profile settings", error);
				reset?.();
			}}
		/>
	);
}
