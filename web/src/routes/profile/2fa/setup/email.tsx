import { Layout } from "@/components";
import { requireAuth, requireCircleOnboardingComplete } from "@/features/auth";
import { EmailSetup } from "@/features/twofa";
import { createFileRoute, useNavigate } from "@tanstack/react-router";

function EmailSetupRoute() {
	const navigate = useNavigate();

	return (
		<Layout>
			<div className="max-w-2xl mx-auto">
				<EmailSetup
					onComplete={() => navigate({ to: "/profile/2fa" })}
					onCancel={() => navigate({ to: "/profile/2fa" })}
				/>
			</div>
		</Layout>
	);
}

export const Route = createFileRoute("/profile/2fa/setup/email")({
	beforeLoad: async (args) => {
		await requireAuth(args);
		await requireCircleOnboardingComplete(args);
	},
	component: EmailSetupRoute,
});
