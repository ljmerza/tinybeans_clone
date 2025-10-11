import { Layout } from "@/components";
import { requireAuth } from "@/features/auth";
import { SmsSetup, use2FAStatus } from "@/features/twofa";
import { createFileRoute, useNavigate } from "@tanstack/react-router";

function SmsSetupRoute() {
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

export const Route = createFileRoute("/profile/2fa/setup/sms")({
	beforeLoad: requireAuth,
	component: SmsSetupRoute,
});
