import { Layout } from "@/components";
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
					onComplete={() => navigate({ to: "/2fa/settings" })}
					onCancel={() => navigate({ to: "/2fa/settings" })}
				/>
			</div>
		</Layout>
	);
}

export const Route = createFileRoute("/2fa/setup/sms")({
	component: SmsSetupRoute,
});
