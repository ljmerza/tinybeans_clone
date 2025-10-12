import { Layout } from "@/components";
import {
	ProfileGeneralSettingsCard,
	ProfileSettingsTabs,
} from "@/features/profile";

export default function ProfileGeneralSettingsPage() {
	return (
		<Layout>
			<ProfileSettingsTabs
				general={<ProfileGeneralSettingsCard />}
				twoFactor={null}
			/>
		</Layout>
	);
}
