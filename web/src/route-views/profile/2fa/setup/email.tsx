import { Layout } from "@/components";
import { EmailSetup } from "@/features/twofa";
import { useNavigate } from "@tanstack/react-router";

export default function EmailSetupPage() {
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
