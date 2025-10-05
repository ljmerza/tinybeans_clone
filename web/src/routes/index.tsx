import { Layout } from "@/components/Layout";
import { useAuthSession } from "@/features/auth";
import { createFileRoute } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

function IndexPage() {
	const session = useAuthSession();
	const { t } = useTranslation();

	return (
		<Layout>
			<div className="text-center">
				<h1 className="heading-1 mb-4">{t('pages.home.welcome')}</h1>
				<p className="text-subtitle mb-8">
					{session.isAuthenticated
						? t('pages.home.authenticated_message')
						: t('pages.home.guest_message')}
				</p>
			</div>
		</Layout>
	);
}

export const Route = createFileRoute("/")({
	component: IndexPage,
});
