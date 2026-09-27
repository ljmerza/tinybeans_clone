import { Layout } from "@/components";
import { KeepFeedPost, useFeedKeep } from "@/features/keeps";
import { Link, getRouteApi } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";
import "react-social-feed/styles.css";

const route = getRouteApi("/keeps/$keepId");

/**
 * A single keep as a feed post — the target of the share button.
 */
export function KeepDetailRouteView() {
	const { t } = useTranslation();
	const { keepId } = route.useParams();
	const { data: keep, isLoading, error } = useFeedKeep(keepId);

	if (isLoading) {
		return (
			<Layout.Loading
				showHeader={false}
				message={t("pages.keep.loading")}
				spinnerSize="sm"
			/>
		);
	}

	return (
		<Layout>
			<div className="container-page space-y-6">
				{keep ? (
					<KeepFeedPost keep={keep} defaultCommentsExpanded />
				) : (
					<div className="py-16 text-center">
						<h1 className="heading-3 mb-2">
							{t("pages.keep.not_found_title")}
						</h1>
						<p className="text-subtitle mb-6">
							{error ? t("pages.keep.not_found_message") : null}
						</p>
					</div>
				)}
				<p className="text-center">
					<Link to="/" className="text-sm underline underline-offset-4">
						{t("pages.keep.back_to_feed")}
					</Link>
				</p>
			</div>
		</Layout>
	);
}
