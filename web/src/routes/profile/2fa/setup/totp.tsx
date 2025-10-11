import { Layout } from "@/components";
import { requireAuth } from "@/features/auth";
import { TotpSetup } from "@/features/twofa";
import { createFileRoute, useNavigate } from "@tanstack/react-router";

function TotpSetupRoute() {
	const navigate = useNavigate();

	return (
		<Layout>
			<div className="max-w-2xl mx-auto">
				<TotpSetup
					onComplete={() => navigate({ to: "/profile/2fa" })}
					onCancel={() => navigate({ to: "/profile/2fa" })}
				/>
			</div>
		</Layout>
	);
}

export const Route = createFileRoute("/profile/2fa/setup/totp")({
	beforeLoad: requireAuth,
	component: TotpSetupRoute,
});
