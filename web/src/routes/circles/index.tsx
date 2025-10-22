import { Layout } from "@/components";
import { circleKeys, circleServices } from "@/features/circles";
import { CirclesIndexRouteView } from "@/route-views/circles/index";
import type { QueryClient } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

export const Route = createFileRoute("/circles/")({
	loader: async ({ context }) => {
		const { queryClient } = context as { queryClient: QueryClient };
		return queryClient.ensureQueryData({
			queryKey: circleKeys.list(),
			queryFn: async () => {
				const response = await circleServices.listMemberships();
				const payload = response.data ?? response;
				return payload?.circles ?? [];
			},
		});
	},
	pendingComponent: CirclesIndexPending,
	errorComponent: CirclesIndexError,
	component: CirclesIndexRouteView,
});

function CirclesIndexPending() {
	const { t } = useTranslation();
	return <Layout.Loading message={t("pages.circles.index.loading")} />;
}

function CirclesIndexError({
	reset,
	error,
}: {
	reset?: () => void;
	error: unknown;
}) {
	const { t } = useTranslation();
	return (
		<Layout.Error
			title={t("pages.circles.index.error_title")}
			message={t("pages.circles.index.error_message")}
			actionLabel={t("pages.circles.index.retry")}
			onAction={() => {
				console.error("Failed to load circles", error);
				reset?.();
			}}
		/>
	);
}
