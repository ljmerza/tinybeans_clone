import { Layout } from "@/components";
import { requireAuth, requireCircleOnboardingComplete } from "@/features/auth";
import {
	ProfileGeneralSettingsCard,
	ProfileNotificationSettingsCard,
	ProfileSettingsTabs,
} from "@/features/profile";
import { createFileRoute } from "@tanstack/react-router";

function ProfileNotificationSettingsPage() {
	return (
		<Layout>
			<ProfileSettingsTabs
				general={<ProfileGeneralSettingsCard />}
				notifications={<ProfileNotificationSettingsCard />}
				twoFactor={null}
			/>
		</Layout>
	);
}

export const Route = createFileRoute("/profile/notifications")({
	beforeLoad: async (args) => {
		await requireAuth(args);
		await requireCircleOnboardingComplete(args);
	},
	component: ProfileNotificationSettingsPage,
});
