import { Layout } from "@/components";
import { SmsSetup, use2FAStatus } from "@/features/twofa";
import { useNavigate } from "@tanstack/react-router";

export default function SmsSetupPage() {
	const navigate = useNavigate();
	const { data: status } = use2FAStatus();

	return (
		<Layout>
			<div className="max-w-2xl mx-auto">
				<SmsSetup
					defaultPhone={status?.phone_number ?? ""}
					onComplete={() => navigate({ to: "/profile/2fa" })}
					onCancel={() => navigate({ to: "/profile/2fa" })}
				/>
			</div>
		</Layout>
	);
}
