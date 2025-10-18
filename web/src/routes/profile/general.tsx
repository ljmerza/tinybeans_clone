import { Layout } from "@/components";
import { requireAuth, requireCircleOnboardingComplete } from "@/features/auth";
import {
	ProfileGeneralSettingsCard,
	ProfileSettingsTabs,
} from "@/features/profile";
import { createFileRoute } from "@tanstack/react-router";

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
	component: ProfileGeneralSettingsPage,
});
