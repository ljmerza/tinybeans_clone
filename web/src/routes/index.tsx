import { Layout } from "@/components/Layout";
import { useAuthSession } from "@/features/auth";
import { createFileRoute } from "@tanstack/react-router";

function IndexPage() {
	const session = useAuthSession();

	return (
		<Layout>
			<div className="text-center">
				<h1 className="heading-1 mb-4">Welcome</h1>
				<p className="text-subtitle mb-8">
					{session.isAuthenticated
						? "You are signed in!"
						: "Get started by signing up or logging in to your account."}
				</p>
			</div>
		</Layout>
	);
}

export const Route = createFileRoute("/")({
	component: IndexPage,
});
