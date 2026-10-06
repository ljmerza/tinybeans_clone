import { Layout } from "@/components/Layout";
import { useAuthSession } from "@/features/auth";
import { LandingPage } from "@/features/landing";
import { HomeFeedView } from "@/route-views/home-feed";
import { createFileRoute } from "@tanstack/react-router";

function IndexPage() {
	const session = useAuthSession();

	if (session.isAuthenticated) {
		return <HomeFeedView />;
	}

	return (
		<Layout>
			<LandingPage />
		</Layout>
	);
}

export const Route = createFileRoute("/")({
	component: IndexPage,
});
