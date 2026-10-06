import { Layout } from "@/components/Layout";
import {
	requireCircleOnboardingComplete,
	useAuthSession,
} from "@/features/auth";
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
	// Every sign-in path lands here, so new users without a circle are sent
	// to onboarding once (guests pass straight through).
	beforeLoad: requireCircleOnboardingComplete,
	component: IndexPage,
});
