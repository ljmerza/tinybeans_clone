/**
 * 2FA Settings Page
 * Manage 2FA configuration, recovery codes, and trusted devices
 */

import { Layout } from "@/components";
import { requireAuth, requireCircleOnboardingComplete } from "@/features/auth";
import {
	ProfileGeneralSettingsCard,
	ProfileSettingsTabs,
} from "@/features/profile";
import {
	TwoFactorRemovalDialog,
	TwoFactorSettingsContent,
	twoFaKeys,
	twoFactorServices,
	useTwoFactorSettings,
} from "@/features/twofa";
import type { QueryClient } from "@tanstack/react-query";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

const twoFactorSettingsPath = "/profile/2fa/" as const;

function TwoFactorSettingsPage() {
	const navigate = useNavigate();
	const { t } = useTranslation();

	const {
		status,
		isLoading,
		methodToRemove,
		removalError,
		switchError,
		removalInProgress,
		switchInProgress,
		requestRemoval,
		cancelRemoval,
		confirmRemoval,
		setAsDefault,
	} = useTwoFactorSettings();

	if (isLoading) {
		return (
			<Layout.Loading
				message={t("twofa.settings.loading_title")}
				description={t("twofa.settings.loading_description")}
			/>
		);
	}

	if (!status) {
		return (
			<Layout.Error
				title={t("twofa.title")}
				description={t("twofa.errors.load_settings")}
				actionLabel={t("common.retry")}
				onAction={() => navigate({ to: "/profile/2fa" })}
			/>
		);
	}

	const handleNavigateToSetup = (path: string) => navigate({ to: path });

	return (
		<Layout>
			<ProfileSettingsTabs
				general={<ProfileGeneralSettingsCard />}
				twoFactor={
					<TwoFactorSettingsContent
						status={status}
						removalError={removalError}
						switchError={switchError}
						methodToRemove={methodToRemove}
						removalInProgress={removalInProgress}
						switchInProgress={switchInProgress}
						onRequestRemoval={requestRemoval}
						onSetAsDefault={setAsDefault}
						onNavigateToSetup={handleNavigateToSetup}
						onBackHome={() => navigate({ to: "/" })}
					/>
				}
			/>

			<TwoFactorRemovalDialog
				method={methodToRemove}
				isLoading={removalInProgress}
				onConfirm={confirmRemoval}
				onCancel={cancelRemoval}
			/>
		</Layout>
	);
}

export const Route = createFileRoute(twoFactorSettingsPath)({
	beforeLoad: async (args) => {
		await requireAuth(args);
		await requireCircleOnboardingComplete(args);
	},
	loader: async ({ context }) => {
		const { queryClient } = context as { queryClient: QueryClient };
		return queryClient.ensureQueryData({
			queryKey: twoFaKeys.status(),
			queryFn: () => twoFactorServices.getStatus(),
		});
	},
	component: TwoFactorSettingsPage,
});
