import { Layout } from "@/components";
import { TotpSetup } from "@/features/twofa";
import { useNavigate } from "@tanstack/react-router";

export default function TotpSetupPage() {
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
