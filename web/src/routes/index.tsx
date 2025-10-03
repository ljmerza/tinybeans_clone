import { Layout } from "@/components/Layout";
import { authStore } from "@/features/auth";
import { createFileRoute } from "@tanstack/react-router";
import { useStore } from "@tanstack/react-store";

function IndexPage() {
	const { accessToken } = useStore(authStore);

	return (
		<Layout>
			<div className="text-center">
				<h1 className="heading-1 mb-4">Welcome</h1>
				<p className="text-subtitle mb-8">
					{accessToken
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
